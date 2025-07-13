package main

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"os/signal"
	"syscall"

	"golang.org/x/sync/errgroup"

	"github.com/omaskery/piedotbot-discord/internal"
	"github.com/omaskery/piedotbot-discord/internal/behaviours"
)

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	logger := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{
		AddSource: true,
		Level:     slog.LevelDebug,
	}))

	logger.InfoContext(ctx, "starting")
	defer logger.InfoContext(ctx, "exiting")

	sc := make(chan os.Signal, 1)
	signal.Notify(sc, syscall.SIGINT, syscall.SIGTERM, os.Interrupt, os.Kill)
	go func() {
		logger.InfoContext(ctx, "listening for exit signal")
		<-sc
		logger.InfoContext(ctx, "received exit signal")
		cancel()
	}()

	if err := errMain(ctx, logger); err != nil {
		logger.With("err", err).Error("exiting with error")
		os.Exit(1)
	}
}

func errMain(ctx context.Context, logger *slog.Logger) error {
	botToken := os.Getenv("BOT_TOKEN")
	if botToken == "" {
		panic("no BOT_TOKEN environment variable provided")
	}
	logger.InfoContext(ctx, "token sanity check", "len", len(botToken))

	bot, err := internal.NewBot(logger, botToken)
	if err != nil {
		return fmt.Errorf("creating bot: %w", err)
	}

	internal.PanicIfErr("adding bot listener", bot.AddListener("dice", behaviours.NewDiceRoller(bot)))
	internal.PanicIfErr("adding bot listener", bot.AddListener("ping", behaviours.NewPingListener(bot)))
	internal.PanicIfErr("adding bot listener", bot.AddListener("activity", behaviours.NewActivityTracker(bot, bot)))

	grp, ctx := errgroup.WithContext(ctx)
	grp.Go(func() error {
		return bot.Start(ctx)
	})

	logger.InfoContext(ctx, "startup complete, running")
	internal.LogIfFails(ctx, logger, "error group returned error", internal.IgnoreIfCancelFn(grp.Wait))
	logger.InfoContext(ctx, "shutting down")

	return nil
}
