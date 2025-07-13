package internal

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
)

func IgnoreIfCancelFn(fn func() error) func() error {
	return func() error {
		return IgnoreIfCancelErr(fn())
	}
}

func IgnoreIfCancelErr(err error) error {
	if errors.Is(err, context.Canceled) {
		return nil
	}
	return err
}

func LogIfFails(ctx context.Context, logger *slog.Logger, msg string, fn func() error) {
	LogIfErr(ctx, logger, msg, fn())
}

func LogIfErr(ctx context.Context, logger *slog.Logger, msg string, err error) {
	if err != nil {
		logger.With("err", err).ErrorContext(ctx, msg)
	}
}

func PanicIfFails(msg string, fn func() error) {
	PanicIfErr(msg, fn())
}

func PanicIfErr(msg string, err error) {
	if err != nil {
		panic(fmt.Sprintf("panic during cleanup %s: %v", msg, err))
	}
}
