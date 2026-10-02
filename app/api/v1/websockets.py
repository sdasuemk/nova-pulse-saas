from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import decode_token
from app.core.logging import logger
from app.models.membership import TenantMember
from app.services.notification_service import ws_manager

router = APIRouter(tags=["WebSockets"])


@router.websocket("/ws/{tenant_id}")
async def tenant_websocket_endpoint(
    websocket: WebSocket,
    tenant_id: str,
    token: str = Query(..., description="JWT access token"),
):
    """
    Real-time WebSocket connection endpoint scoped to a specific tenant workspace.
    Authenticates user via token query param and confirms tenant membership.
    """
    # 1. Authenticate JWT token
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id or payload.get("type") != "access":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception as e:
        logger.warning(f"WebSocket auth failed: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Check tenant membership
    async with AsyncSessionLocal() as session:
        query = select(TenantMember).where(
            TenantMember.tenant_id == tenant_id,
            TenantMember.user_id == user_id,
        )
        res = await session.execute(query)
        membership = res.scalar_one_or_none()
        if not membership:
            logger.warning(f"User {user_id} denied WebSocket access to tenant {tenant_id}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    # 3. Connect and listen
    await ws_manager.connect(tenant_id, websocket)
    try:
        while True:
            # Keep connection alive & handle incoming pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(tenant_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(tenant_id, websocket)
