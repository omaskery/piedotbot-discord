package behaviours

import (
	"context"
	"fmt"
	"log/slog"
	"math/rand"
	"regexp"
	"strconv"
	"strings"

	"github.com/omaskery/piedotbot-discord/internal"
)

const rollCommandStr = "!roll"

var rollRegex = regexp.MustCompile("(\\d+)\\s*d\\s*(\\d+)\\s*([+-](\\d+))?")

type DiceRoller struct {
	responder Responder
}

func NewDiceRoller(responder Responder) *DiceRoller {
	return &DiceRoller{
		responder: responder,
	}
}

func (dr *DiceRoller) HandleMessage(ctx context.Context, logger *slog.Logger, msg *internal.MessageCreated) error {
	const emojiAnnoyed = "😒"
	const emojiSad = "😢"

	parts := strings.SplitN(strings.Trim(msg.Content, " "), " ", 2)
	if len(parts) < 2 || parts[0] != rollCommandStr {
		return nil
	}

	rollStr := parts[1]

	groups := rollRegex.FindStringSubmatch(rollStr)
	logger = logger.With("roll-str", rollStr, "groups", groups)

	helper := newResponseHelper(logger, dr.responder, msg)

	if len(groups) < 3 {
		return helper.respondError(ctx, logger, respondInChannel, fmt.Errorf("malformed command"), emojiAnnoyed, "malformed command")
	}

	diceCount, err := strconv.Atoi(groups[1])
	if err != nil {
		return helper.respondError(ctx, logger, respondInChannel, err, emojiAnnoyed, "failed to parse dice count")
	}
	sideCount, err := strconv.Atoi(groups[2])
	if err != nil {
		return helper.respondError(ctx, logger, respondInChannel, err, emojiAnnoyed, "failed to parse side count")
	}

	maxDiceCount := 30
	if diceCount > maxDiceCount {
		return helper.respondf(ctx, respondInChannel, emojiSad, "but I only have %v dice... 😰", maxDiceCount)
	}
	if diceCount < 1 {
		return dr.responder.AddReaction(ctx, msg.Channel.ID, msg.ID, emojiAnnoyed)
	}

	maxSideCount := 100
	if sideCount > maxSideCount {
		return helper.respondf(ctx, respondInChannel, emojiSad, "but I only have dice with up to %v sides... 😰", maxSideCount)
	}
	if sideCount < 1 {
		return dr.responder.AddReaction(ctx, msg.Channel.ID, msg.ID, emojiAnnoyed)
	}

	offset := 0

	if groups[3] != "" {
		offset, err = strconv.Atoi(groups[3])
		if err != nil {
			return helper.respondError(ctx, logger, respondInChannel, err, emojiAnnoyed, "failed to parse offset")
		}
	}

	logger.Info("rolling dice", "dice", diceCount, "sides", sideCount, "offset", offset)

	rollResponse := strings.Builder{}
	rollResponse.WriteString(fmt.Sprintf("<@%v> rolled ", msg.Author.ID))

	rolls := make([]int, 0, diceCount)
	sum := 0
	for i := 0; i < diceCount; i++ {
		if i > 0 && i < (diceCount-1) {
			rollResponse.WriteString(", ")
		} else if i > 0 && i == (diceCount-1) {
			rollResponse.WriteString(" and ")
		}

		roll := rand.Intn(sideCount-1) + 1
		rollResponse.WriteString(fmt.Sprintf("%v", roll))
		sum += roll
		rolls = append(rolls, roll)
	}
	if diceCount > 1 {
		rollResponse.WriteString(fmt.Sprintf(" for a total of %v", sum))
	}

	if offset < 0 || offset > 0 {
		sum += offset
		rollResponse.WriteString(fmt.Sprintf(", with %v the total becomes %v", offset, sum))
	}

	return helper.respond(ctx, respondInChannel, "", rollResponse.String())
}

func (dr *DiceRoller) VoiceStateUpdated(context.Context, *slog.Logger, *internal.VoiceStateUpdate) error {
	return nil
}
