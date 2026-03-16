from __future__ import annotations

import pytest
import hikari

from hikaripersist.rule import (
    ChannelRule,
    GuildRule,
    MemberRule,
    RoleRule,
    Rule,
)

# ---------------------------------------------------------------------------
# Snowflake helpers
# ---------------------------------------------------------------------------

def sf(n: int) -> hikari.Snowflake:
    return hikari.Snowflake(n)


# Common IDs used across tests
GUILD_A   = sf(1)
GUILD_B   = sf(2)
CHANNEL_A = sf(10)
CHANNEL_B = sf(11)
USER_A    = sf(20)
USER_B    = sf(21)
MESSAGE_A = sf(30)
MESSAGE_B = sf(31)
ROLE_A    = sf(40)
ROLE_B    = sf(41)


# ---------------------------------------------------------------------------
# ChannelRule
# ---------------------------------------------------------------------------

class TestChannelRule:

    # --- No rules (default) ---

    def test_default_allows_everything(self) -> None:
        rule = ChannelRule()
        assert rule.can_cache(CHANNEL_A, GUILD_A) is True

    # --- channel_denylist ---

    def test_channel_denylist_blocks_listed(self) -> None:
        rule = ChannelRule(channel_denylist=[CHANNEL_A])
        assert rule.can_cache(CHANNEL_A, GUILD_A) is False

    def test_channel_denylist_allows_unlisted(self) -> None:
        rule = ChannelRule(channel_denylist=[CHANNEL_A])
        assert rule.can_cache(CHANNEL_B, GUILD_A) is True

    def test_channel_denylist_multiple(self) -> None:
        rule = ChannelRule(channel_denylist=[CHANNEL_A, CHANNEL_B])
        assert rule.can_cache(CHANNEL_A, GUILD_A) is False
        assert rule.can_cache(CHANNEL_B, GUILD_A) is False

    # --- channel_allowlist ---

    def test_channel_allowlist_allows_listed(self) -> None:
        rule = ChannelRule(channel_allowlist=[CHANNEL_A])
        assert rule.can_cache(CHANNEL_A, GUILD_A) is True

    def test_channel_allowlist_blocks_unlisted(self) -> None:
        rule = ChannelRule(channel_allowlist=[CHANNEL_A])
        assert rule.can_cache(CHANNEL_B, GUILD_A) is False

    def test_channel_allowlist_multiple(self) -> None:
        rule = ChannelRule(channel_allowlist=[CHANNEL_A, CHANNEL_B])
        assert rule.can_cache(CHANNEL_A, GUILD_A) is True
        assert rule.can_cache(CHANNEL_B, GUILD_A) is True

    # --- guild_denylist ---

    def test_guild_denylist_blocks_listed(self) -> None:
        rule = ChannelRule(guild_denylist=[GUILD_A])
        assert rule.can_cache(CHANNEL_A, GUILD_A) is False

    def test_guild_denylist_allows_unlisted(self) -> None:
        rule = ChannelRule(guild_denylist=[GUILD_A])
        assert rule.can_cache(CHANNEL_A, GUILD_B) is True

    # --- guild_allowlist ---

    def test_guild_allowlist_allows_listed(self) -> None:
        rule = ChannelRule(guild_allowlist=[GUILD_A])
        assert rule.can_cache(CHANNEL_A, GUILD_A) is True

    def test_guild_allowlist_blocks_unlisted(self) -> None:
        rule = ChannelRule(guild_allowlist=[GUILD_A])
        assert rule.can_cache(CHANNEL_A, GUILD_B) is False

    # --- denylist takes priority over allowlist ---

    def test_denylist_takes_priority_over_allowlist_channel(self) -> None:
        rule = ChannelRule(
            channel_denylist=[CHANNEL_A],
            channel_allowlist=[CHANNEL_A],
        )
        assert rule.can_cache(CHANNEL_A, GUILD_A) is False

    def test_denylist_takes_priority_over_allowlist_guild(self) -> None:
        rule = ChannelRule(
            guild_denylist=[GUILD_A],
            guild_allowlist=[GUILD_A],
        )
        assert rule.can_cache(CHANNEL_A, GUILD_A) is False

    # --- combined rules ---

    def test_channel_passes_guild_blocked(self) -> None:
        rule = ChannelRule(guild_denylist=[GUILD_A])
        assert rule.can_cache(CHANNEL_A, GUILD_A) is False

    def test_guild_passes_channel_blocked(self) -> None:
        rule = ChannelRule(channel_denylist=[CHANNEL_A])
        assert rule.can_cache(CHANNEL_A, GUILD_A) is False

    def test_both_allowlists_both_pass(self) -> None:
        rule = ChannelRule(
            channel_allowlist=[CHANNEL_A],
            guild_allowlist=[GUILD_A],
        )
        assert rule.can_cache(CHANNEL_A, GUILD_A) is True

    def test_both_allowlists_channel_fails(self) -> None:
        rule = ChannelRule(
            channel_allowlist=[CHANNEL_A],
            guild_allowlist=[GUILD_A],
        )
        assert rule.can_cache(CHANNEL_B, GUILD_A) is False

    def test_both_allowlists_guild_fails(self) -> None:
        rule = ChannelRule(
            channel_allowlist=[CHANNEL_A],
            guild_allowlist=[GUILD_A],
        )
        assert rule.can_cache(CHANNEL_A, GUILD_B) is False

    # --- type errors ---

    def test_invalid_channel_denylist_type(self) -> None:
        with pytest.raises(TypeError):
            ChannelRule(channel_denylist="not_an_iterable_of_snowflakes")  # type: ignore

    def test_invalid_guild_allowlist_type(self) -> None:
        with pytest.raises(TypeError):
            ChannelRule(guild_allowlist=123)  # type: ignore


# ---------------------------------------------------------------------------
# GuildRule
# ---------------------------------------------------------------------------

class TestGuildRule:

    def test_default_allows_everything(self) -> None:
        rule = GuildRule()
        assert rule.can_cache(GUILD_A) is True

    def test_guild_denylist_blocks_listed(self) -> None:
        rule = GuildRule(guild_denylist=[GUILD_A])
        assert rule.can_cache(GUILD_A) is False

    def test_guild_denylist_allows_unlisted(self) -> None:
        rule = GuildRule(guild_denylist=[GUILD_A])
        assert rule.can_cache(GUILD_B) is True

    def test_guild_allowlist_allows_listed(self) -> None:
        rule = GuildRule(guild_allowlist=[GUILD_A])
        assert rule.can_cache(GUILD_A) is True

    def test_guild_allowlist_blocks_unlisted(self) -> None:
        rule = GuildRule(guild_allowlist=[GUILD_A])
        assert rule.can_cache(GUILD_B) is False

    def test_denylist_takes_priority_over_allowlist(self) -> None:
        rule = GuildRule(
            guild_denylist=[GUILD_A],
            guild_allowlist=[GUILD_A],
        )
        assert rule.can_cache(GUILD_A) is False

    def test_empty_allowlist_allows_all(self) -> None:
        rule = GuildRule(guild_allowlist=[])
        assert rule.can_cache(GUILD_A) is True

    def test_invalid_type(self) -> None:
        with pytest.raises(TypeError):
            GuildRule(guild_denylist=42)  # type: ignore


# ---------------------------------------------------------------------------
# MemberRule
# ---------------------------------------------------------------------------

class TestMemberRule:

    def test_default_allows_everything(self) -> None:
        rule = MemberRule()
        assert rule.can_cache(GUILD_A, USER_A) is True

    def test_guild_denylist_blocks(self) -> None:
        rule = MemberRule(guild_denylist=[GUILD_A])
        assert rule.can_cache(GUILD_A, USER_A) is False

    def test_guild_denylist_allows_other_guild(self) -> None:
        rule = MemberRule(guild_denylist=[GUILD_A])
        assert rule.can_cache(GUILD_B, USER_A) is True

    def test_guild_allowlist_blocks_unlisted(self) -> None:
        rule = MemberRule(guild_allowlist=[GUILD_A])
        assert rule.can_cache(GUILD_B, USER_A) is False

    def test_user_denylist_blocks(self) -> None:
        rule = MemberRule(user_denylist=[USER_A])
        assert rule.can_cache(GUILD_A, USER_A) is False

    def test_user_denylist_allows_other_user(self) -> None:
        rule = MemberRule(user_denylist=[USER_A])
        assert rule.can_cache(GUILD_A, USER_B) is True

    def test_user_allowlist_blocks_unlisted(self) -> None:
        rule = MemberRule(user_allowlist=[USER_A])
        assert rule.can_cache(GUILD_A, USER_B) is False

    def test_user_allowlist_allows_listed(self) -> None:
        rule = MemberRule(user_allowlist=[USER_A])
        assert rule.can_cache(GUILD_A, USER_A) is True

    def test_guild_denylist_takes_priority(self) -> None:
        rule = MemberRule(
            guild_denylist=[GUILD_A],
            guild_allowlist=[GUILD_A],
        )
        assert rule.can_cache(GUILD_A, USER_A) is False

    def test_user_denylist_takes_priority(self) -> None:
        rule = MemberRule(
            user_denylist=[USER_A],
            user_allowlist=[USER_A],
        )
        assert rule.can_cache(GUILD_A, USER_A) is False

    def test_guild_blocked_user_allowed(self) -> None:
        rule = MemberRule(
            guild_denylist=[GUILD_A],
            user_allowlist=[USER_A],
        )
        assert rule.can_cache(GUILD_A, USER_A) is False

    def test_guild_allowed_user_blocked(self) -> None:
        rule = MemberRule(
            guild_allowlist=[GUILD_A],
            user_denylist=[USER_A],
        )
        assert rule.can_cache(GUILD_A, USER_A) is False

    def test_both_pass(self) -> None:
        rule = MemberRule(
            guild_allowlist=[GUILD_A],
            user_allowlist=[USER_A],
        )
        assert rule.can_cache(GUILD_A, USER_A) is True

    def test_invalid_type(self) -> None:
        with pytest.raises(TypeError):
            MemberRule(user_denylist="bad")  # type: ignore


# ---------------------------------------------------------------------------
# RoleRule
# ---------------------------------------------------------------------------

class TestRoleRule:

    def test_default_allows_everything(self) -> None:
        rule = RoleRule()
        assert rule.can_cache(GUILD_A, ROLE_A) is True

    def test_guild_denylist(self) -> None:
        rule = RoleRule(guild_denylist=[GUILD_A])
        assert rule.can_cache(GUILD_A, ROLE_A) is False
        assert rule.can_cache(GUILD_B, ROLE_A) is True

    def test_guild_allowlist(self) -> None:
        rule = RoleRule(guild_allowlist=[GUILD_A])
        assert rule.can_cache(GUILD_A, ROLE_A) is True
        assert rule.can_cache(GUILD_B, ROLE_A) is False

    def test_role_denylist(self) -> None:
        rule = RoleRule(role_denylist=[ROLE_A])
        assert rule.can_cache(GUILD_A, ROLE_A) is False
        assert rule.can_cache(GUILD_A, ROLE_B) is True

    def test_role_allowlist(self) -> None:
        rule = RoleRule(role_allowlist=[ROLE_A])
        assert rule.can_cache(GUILD_A, ROLE_A) is True
        assert rule.can_cache(GUILD_A, ROLE_B) is False

    def test_guild_denylist_takes_priority(self) -> None:
        rule = RoleRule(
            guild_denylist=[GUILD_A],
            guild_allowlist=[GUILD_A],
        )
        assert rule.can_cache(GUILD_A, ROLE_A) is False

    def test_role_denylist_takes_priority(self) -> None:
        rule = RoleRule(
            role_denylist=[ROLE_A],
            role_allowlist=[ROLE_A],
        )
        assert rule.can_cache(GUILD_A, ROLE_A) is False

    def test_guild_blocked_role_irrelevant(self) -> None:
        rule = RoleRule(
            guild_denylist=[GUILD_A],
            role_allowlist=[ROLE_A],
        )
        assert rule.can_cache(GUILD_A, ROLE_A) is False

    def test_both_pass(self) -> None:
        rule = RoleRule(
            guild_allowlist=[GUILD_A],
            role_allowlist=[ROLE_A],
        )
        assert rule.can_cache(GUILD_A, ROLE_A) is True

    def test_invalid_type(self) -> None:
        with pytest.raises(TypeError):
            RoleRule(role_allowlist="bad")  # type: ignore


# ---------------------------------------------------------------------------
# Rule (composite)
# ---------------------------------------------------------------------------

class TestRule:

    def test_default_construction(self) -> None:
        rule = Rule()
        assert isinstance(rule._channel, ChannelRule)
        assert isinstance(rule._guild, GuildRule)
        assert isinstance(rule._member, MemberRule)
        assert isinstance(rule._role, RoleRule)

    def test_custom_channel_rule(self) -> None:
        channel_rule = ChannelRule(channel_denylist=[CHANNEL_A])
        rule = Rule(channel=channel_rule)
        assert rule._channel is channel_rule

    def test_custom_guild_rule(self) -> None:
        guild_rule = GuildRule(guild_denylist=[GUILD_A])
        rule = Rule(guild=guild_rule)
        assert rule._guild is guild_rule

    def test_custom_member_rule(self) -> None:
        member_rule = MemberRule(user_denylist=[USER_A])
        rule = Rule(member=member_rule)
        assert rule._member is member_rule

    def test_custom_role_rule(self) -> None:
        role_rule = RoleRule(role_denylist=[ROLE_A])
        rule = Rule(role=role_rule)
        assert rule._role is role_rule

    def test_invalid_channel_type(self) -> None:
        with pytest.raises(TypeError):
            Rule(channel=GuildRule())  # type: ignore

    def test_invalid_guild_type(self) -> None:
        with pytest.raises(TypeError):
            Rule(guild=ChannelRule())  # type: ignore

    def test_invalid_member_type(self) -> None:
        with pytest.raises(TypeError):
            Rule(member=RoleRule())  # type: ignore

    def test_invalid_message_type(self) -> None:
        with pytest.raises(TypeError):
            Rule(message=MemberRule())  # type: ignore

    def test_all_custom_rules(self) -> None:
        rule = Rule(
            channel=ChannelRule(channel_denylist=[CHANNEL_A]),
            guild=GuildRule(guild_denylist=[GUILD_A]),
            member=MemberRule(user_denylist=[USER_A]),
            role=RoleRule(role_denylist=[ROLE_A]),
        )
        assert rule._channel._channel_denylist == {CHANNEL_A}
        assert rule._guild._guild_denylist == {GUILD_A}
        assert rule._member._user_denylist == {USER_A}
        assert rule._role._role_denylist == {ROLE_A}


# ---------------------------------------------------------------------------
# to_snowflake_set / verify_type edge cases
# ---------------------------------------------------------------------------

class TestHelpers:

    def test_snowflakeish_int_is_accepted(self) -> None:
        rule = GuildRule(guild_denylist=[1, 2, 3])
        assert sf(1) in rule._guild_denylist
        assert sf(2) in rule._guild_denylist
        assert sf(3) in rule._guild_denylist

    def test_snowflakeish_snowflake_is_accepted(self) -> None:
        rule = GuildRule(guild_denylist=[sf(1)])
        assert sf(1) in rule._guild_denylist

    def test_none_produces_empty_set(self) -> None:
        rule = GuildRule(guild_denylist=None)
        assert rule._guild_denylist == set()

    def test_empty_iterable_produces_empty_set(self) -> None:
        rule = GuildRule(guild_denylist=[])
        assert rule._guild_denylist == set()

    def test_generator_is_accepted(self) -> None:
        rule = GuildRule(guild_denylist=(sf(i) for i in range(3)))
        assert sf(0) in rule._guild_denylist
        assert sf(1) in rule._guild_denylist
        assert sf(2) in rule._guild_denylist

    def test_duplicate_ids_deduplicated(self) -> None:
        rule = GuildRule(guild_denylist=[GUILD_A, GUILD_A, GUILD_A])
        assert len(rule._guild_denylist) == 1
