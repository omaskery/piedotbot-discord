package behaviours

import (
	"context"
	"fmt"
	"log/slog"

	"github.com/omaskery/piedotbot-discord/internal"
)

type Responder interface {
	SendMessage(ctx context.Context, channelID, message string) error
	AddReaction(ctx context.Context, channelID, messageID, emojiID string) error
}

type responseHelper struct {
	logger    *slog.Logger
	responder Responder
	original  *internal.MessageCreated
}

func newResponseHelper(logger *slog.Logger, responder Responder, original *internal.MessageCreated) *responseHelper {
	return &responseHelper{
		logger:    logger,
		responder: responder,
		original:  original,
	}
}

type responseFn func(ctx context.Context, r Responder, original *internal.MessageCreated, response string) error

func respondInChannel(ctx context.Context, r Responder, original *internal.MessageCreated, response string) error {
	return r.SendMessage(ctx, original.Channel.ID, response)
}

func (rh *responseHelper) respond(ctx context.Context, fn responseFn, emojiID string, response string) error {
	if err := fn(ctx, rh.responder, rh.original, response); err != nil {
		return fmt.Errorf("replying to message: %w", err)
	}

	if emojiID != "" {
		if err := rh.responder.AddReaction(ctx, rh.original.Channel.ID, rh.original.ID, emojiID); err != nil {
			rh.logger.ErrorContext(ctx, "error reacting to message", "err", err)
		}
	}

	return nil
}

func (rh *responseHelper) respondf(ctx context.Context, fn responseFn, emojiID string, format string, args ...any) error {
	if err := fn(ctx, rh.responder, rh.original, fmt.Sprintf(format, args...)); err != nil {
		return fmt.Errorf("replying to message: %w", err)
	}

	if err := rh.responder.AddReaction(ctx, rh.original.Channel.ID, rh.original.ID, emojiID); err != nil {
		rh.logger.ErrorContext(ctx, "error reacting to message", "err", err)
	}

	return nil
}

func (rh *responseHelper) respondError(ctx context.Context, logger *slog.Logger, fn responseFn, err error, emojiID, response string) error {
	logger.ErrorContext(ctx, response, "err", err)
	if err := fn(ctx, rh.responder, rh.original, response); err != nil {
		return fmt.Errorf("replying to message: %w", err)
	}

	if err := rh.responder.AddReaction(ctx, rh.original.Channel.ID, rh.original.ID, emojiID); err != nil {
		rh.logger.ErrorContext(ctx, "error reacting to message", "err", err)
	}

	return nil
}
