package behaviours

import (
	"context"
	"log/slog"

	"github.com/omaskery/piedotbot-discord/internal"
)

type PingListener struct {
	responder Responder
}

func NewPingListener(responder Responder) *PingListener {
	return &PingListener{
		responder: responder,
	}
}

func (pl *PingListener) HandleMessage(ctx context.Context, _ *slog.Logger, msg *internal.MessageCreated) error {
	if msg.Content != "!ping" {
		return nil
	}

	return pl.responder.AddReaction(ctx, msg.Channel.ID, msg.ID, "👍")
}

func (pl *PingListener) VoiceStateUpdated(context.Context, *slog.Logger, *internal.VoiceStateUpdate) error {
	return nil
}
