from __future__ import annotations

import base64
import http
import time
import json

import lark_oapi.ws.client as ws_client_module
from lark_oapi.core.const import UTF_8
from lark_oapi.core.json import JSON
from lark_oapi.core.log import logger
from lark_oapi.ws.const import (
    HEADER_BIZ_RT,
    HEADER_MESSAGE_ID,
    HEADER_SEQ,
    HEADER_SUM,
    HEADER_TRACE_ID,
    HEADER_TYPE,
)
from lark_oapi.ws.enum import MessageType
from lark_oapi.ws.model import Response
from lark_oapi.ws.pb.pbbp2_pb2 import Frame


class PatchedWSClient(ws_client_module.Client):
    async def _handle_data_frame(self, frame: Frame):
        hs = frame.headers
        msg_id = ws_client_module._get_by_key(hs, HEADER_MESSAGE_ID)
        trace_id = ws_client_module._get_by_key(hs, HEADER_TRACE_ID)
        sum_ = ws_client_module._get_by_key(hs, HEADER_SUM)
        seq = ws_client_module._get_by_key(hs, HEADER_SEQ)
        type_ = ws_client_module._get_by_key(hs, HEADER_TYPE)

        pl = frame.payload
        if int(sum_) > 1:
            pl = self._combine(msg_id, int(sum_), int(seq), pl)
            if pl is None:
                return

        message_type = MessageType(type_)

        event_type = None
        if message_type in {MessageType.EVENT, MessageType.CARD}:
            try:
                obj = json.loads(pl.decode(UTF_8))
                header = obj.get("header") if isinstance(obj, dict) else None
                event = obj.get("event") if isinstance(obj, dict) else None
                if isinstance(header, dict):
                    event_type = header.get("event_type")
                if event_type is None and isinstance(event, dict):
                    event_type = event.get("type")
            except Exception:
                event_type = None

        logger.info(
            self._fmt_log(
                "receive frame, message_type: {}, event_type: {}, message_id: {}, trace_id: {}",
                message_type.value,
                event_type,
                msg_id,
                trace_id,
            )
        )
        logger.debug(
            self._fmt_log(
                "receive message, message_type: {}, message_id: {}, trace_id: {}, payload: {}",
                message_type.value,
                msg_id,
                trace_id,
                pl.decode(UTF_8),
            )
        )

        resp = Response(code=http.HTTPStatus.OK)
        try:
            start = int(round(time.time() * 1000))
            if message_type in {MessageType.EVENT, MessageType.CARD}:
                result = self._event_handler.do_without_validation(pl)
            else:
                return

            end = int(round(time.time() * 1000))
            header = hs.add()
            header.key = HEADER_BIZ_RT
            header.value = str(end - start)
            if result is not None:
                resp.data = base64.b64encode(JSON.marshal(result).encode(UTF_8))
        except Exception as e:
            logger.error(
                self._fmt_log(
                    "handle message failed, message_type: {}, message_id: {}, trace_id: {}, err: {}",
                    message_type.value,
                    msg_id,
                    trace_id,
                    e,
                )
            )
            err_msg = str(e)
            if "processor not found" in err_msg or "callback processor not found" in err_msg:
                resp = Response(code=http.HTTPStatus.OK)
            else:
                resp = Response(code=http.HTTPStatus.INTERNAL_SERVER_ERROR)

        frame.payload = JSON.marshal(resp).encode(UTF_8)
        await self._write_message(frame.SerializeToString())
