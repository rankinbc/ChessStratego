"""Discriminated-union message envelope for the websocket wire format.

Every message, both directions, is {type, payload, seq}. Inbound types are
parsed strictly through the ClientMessage union below — malformed input
becomes a typed "error" reply, never a crashed loop.

THE WIRE CONTRACT: the MSG constants in game_client/js/protocol.js mirror
the message type literals here exactly. Change both sides together or not
at all.
"""

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter

Pos = tuple[int, int]

# Outbound (server -> client) message types.
SNAPSHOT = "snapshot"
JOINED = "joined"
ERROR = "error"


class JoinPayload(BaseModel):
    name: str


class RejoinPayload(BaseModel):
    token: str


class EmptyPayload(BaseModel):
    pass


class PlacementItem(BaseModel):
    piece_id: str
    pos: Pos


class SetupSubmitPayload(BaseModel):
    placements: list[PlacementItem]


class MovePayload(BaseModel):
    piece_id: str
    to: Pos


class JoinMessage(BaseModel):
    type: Literal["join"]
    payload: JoinPayload
    seq: int = 0


class RejoinMessage(BaseModel):
    type: Literal["rejoin"]
    payload: RejoinPayload
    seq: int = 0


class StartGameMessage(BaseModel):
    type: Literal["start_game"]
    payload: EmptyPayload = Field(default_factory=EmptyPayload)
    seq: int = 0


class SetupSubmitMessage(BaseModel):
    type: Literal["setup_submit"]
    payload: SetupSubmitPayload
    seq: int = 0


class SetupAutoMessage(BaseModel):
    type: Literal["setup_auto"]
    payload: EmptyPayload = Field(default_factory=EmptyPayload)
    seq: int = 0


class MoveMessage(BaseModel):
    type: Literal["move"]
    payload: MovePayload
    seq: int = 0


class ResyncMessage(BaseModel):
    type: Literal["resync"]
    payload: EmptyPayload = Field(default_factory=EmptyPayload)
    seq: int = 0


ClientMessage = Annotated[
    Union[
        JoinMessage,
        RejoinMessage,
        StartGameMessage,
        SetupSubmitMessage,
        SetupAutoMessage,
        MoveMessage,
        ResyncMessage,
    ],
    Field(discriminator="type"),
]

_CLIENT_MESSAGE_ADAPTER: TypeAdapter[Any] = TypeAdapter(ClientMessage)


def parse_client_message(text: str | bytes) -> Any:
    """Parse one inbound frame; raises pydantic.ValidationError on bad input."""
    return _CLIENT_MESSAGE_ADAPTER.validate_json(text)


def envelope(type_: str, payload: Any, seq: int) -> dict[str, Any]:
    return {"type": type_, "payload": payload, "seq": seq}
