package behaviours

import (
	"fmt"
	"github.com/bwmarrin/discordgo"
	"github.com/go-logr/logr"
	"math/rand"
	"regexp"
	"strconv"
	"strings"
)

func RollDice(_ logr.Logger, session *discordgo.Session, msg *discordgo.MessageCreate) error {
	regex, err := regexp.Compile("!roll\\s+(\\d+)\\s*d\\s*(\\d+)(\\s*[+-](\\d+))?")
	if err != nil {
		return fmt.Errorf("failed to compile dice regexp: %v", err)
	}

	groups := regex.FindStringSubmatch(msg.Content)
	if len(groups) < 3 {
		return nil
	}

	diceCount, _ := strconv.Atoi(groups[1])
	sideCount, _ := strconv.Atoi(groups[2])

	maxDiceCount := 30
	if diceCount > maxDiceCount {
		_, err := session.ChannelMessageSend(msg.ChannelID, fmt.Sprintf("but I only have %v dice... 😰", maxDiceCount))
		_ = session.MessageReactionAdd(msg.ChannelID, msg.ID, "😢")
		return err
	}
	if diceCount < 1 {
		return session.MessageReactionAdd(msg.ChannelID, msg.ID, "😒")
	}

	maxSideCount := 100
	if sideCount > maxSideCount {
		_, err := session.ChannelMessageSend(msg.ChannelID, fmt.Sprintf("but I only have dice with up to %v sides... 😰", maxSideCount))
		_ = session.MessageReactionAdd(msg.ChannelID, msg.ID, "😢")
		return err
	}
	if sideCount < 1 {
		return session.MessageReactionAdd(msg.ChannelID, msg.ID, "😒")
	}

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

		roll := rand.Intn(sideCount - 1) + 1
		rollResponse.WriteString(fmt.Sprintf("%v", roll))
		sum += roll
		rolls = append(rolls, roll)
	}
	rollResponse.WriteString(fmt.Sprintf(" for a total of %v", sum))

	if len(groups) > 3 {
		offset, _ := strconv.Atoi(strings.TrimSpace(groups[3]))
		if offset < 0 || offset > 0 {
			sum += offset
			rollResponse.WriteString(fmt.Sprintf(", with %v the total becomes %v", offset, sum))
		}
	}

	_, err = session.ChannelMessageSend(msg.ChannelID, rollResponse.String())
	return err
}
