from tctk import BotFeature

# This needs to emit eight events corresponding to
#   1. The duel offer being initiated
#   2. The seven end states of a duel offer
#       a. Five errors
#       b. Denial
#       c. Completion
#   3. (1.) and (2.a.) Amount to six handlers which are
#       MessageEventType -> DuelOfferRecordType
#   4. (2.b.) and (2.c.) Require handlers of type
#       MessageEventType -> Predicate<MessageEventType, DuelOfferRecordType> ->
#           DuelOfferRecordType -> DuelOfferRecordType

class Regex:

    duel_complete_re = "(?P) won the Duel vs johnny_starr PogChamp appearingloki won 5 eastcoins FeelsGoodMan"

class DuelFeature(BotFeature):
    pass