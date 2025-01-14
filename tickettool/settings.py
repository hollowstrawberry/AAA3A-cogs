from AAA3A_utils import Buttons, Dropdown  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from .utils import EmojiLabelDescriptionValueConverter


_ = Translator("TicketTool", __file__)


class ProfileConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        if len(argument) > 10:
            raise commands.BadArgument(_("This profile does not exist."))
        profiles = await ctx.bot.get_cog("TicketTool").config.guild(ctx.guild).profiles()
        if argument.lower() not in profiles:
            raise commands.BadArgument(_("This profile does not exist."))
        return argument.lower()


@cog_i18n(_)
class settings(commands.Cog):
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @commands.hybrid_group(name="settickettool", aliases=["tickettoolset"])
    async def configuration(self, ctx: commands.Context) -> None:
        """Configure TicketTool for your server."""
        pass

    @configuration.command(name="message")
    async def message(
        self,
        ctx: commands.Context,
        profile: ProfileConverter,
        channel: typing.Optional[discord.TextChannel],
        message: typing.Optional[commands.MessageConverter],
        reason_options: commands.Greedy[EmojiLabelDescriptionValueConverter],
    ) -> None:
        """Send a message with a button to open a ticket or dropdown with possible reasons.

        Example:
        `[p]setticket message #general "🐛|Report a bug|If you find a bug, report it here.|bug" "⚠️|Report a user|If you find a malicious user, report it here.|user"`
        `[p]setticket 1234567890-0987654321`
        """
        if channel is None:
            channel = ctx.channel
        if reason_options == []:
            reason_options = None
        if message is not None and message.author != ctx.guild.me:
            await ctx.send(
                _("I have to be the author of the message for the interaction to work.")
            )
            return
        config = await self.get_config(ctx.guild, profile)
        actual_color = config["color"]
        actual_thumbnail = config["thumbnail"]
        embed: discord.Embed = discord.Embed()
        embed.title = config["embed_button"]["title"]
        embed.description = config["embed_button"]["description"].replace(
            "{prefix}", f"{ctx.prefix}"
        )
        embed.set_image(
            url=config["embed_button"]["image"]
        )
        embed.set_thumbnail(url=actual_thumbnail)
        embed.color = actual_color
        embed.set_footer(
            text=ctx.guild.name,
            icon_url=ctx.guild.icon,
        )
        if reason_options is None:
            buttons_config = await self.config.guild(ctx.guild).buttons.all()
            view = Buttons(
                timeout=None,
                buttons=[
                    {
                        "style": 2,
                        "label": _("Create ticket"),
                        "emoji": "🎟️",
                        "custom_id": "create_ticket_button",
                        "disabled": False,
                    }
                ],
                function=self.on_button_interaction,
                infinity=True,
            )
            if message is None:
                message = await channel.send(embed=embed, view=view)
            else:
                await message.edit(view=view)
            self.cogsutils.views.append(view)
            buttons_config[f"{message.channel.id}-{message.id}"] = {"profile": profile}
            await self.config.guild(ctx.guild).buttons.set(buttons_config)
        else:
            if getattr(ctx, "interaction", None) is None:
                try:
                    for emoji, label, description, value in reason_options[:19]:
                        await ctx.message.add_reaction(emoji)
                except discord.HTTPException:
                    await ctx.send(
                        _(
                            "An emoji you selected seems invalid. Check that it is an emoji. If you have Nitro, you may have used a custom emoji from another server."
                        )
                    )
                    return
            dropdowns_config = await self.config.guild(ctx.guild).dropdowns.all()
            all_options = []
            for emoji, label, description, value in reason_options:
                emoji = emoji.id if hasattr(emoji, "id") else emoji
                try:
                    int(emoji)
                except ValueError:
                    e = emoji
                else:
                    e = self.bot.get_emoji(int(emoji))
                all_options.append(
                    {
                        "label": label,
                        "value": value,
                        "description": description,
                        "emoji": e,
                        "default": False,
                    }
                )
            view = Dropdown(
                timeout=None,
                placeholder=config["embed_button"]["placeholder_dropdown"],
                min_values=0,
                max_values=1,
                options=all_options,
                function=self.on_dropdown_interaction,
                infinity=True,
                custom_id="create_ticket_dropdown",
            )
            if message is None:
                message = await channel.send(embed=embed, view=view)
            else:
                await message.edit(view=view)
            self.cogsutils.views.append(view)
            dropdowns_config[f"{message.channel.id}-{message.id}"] = [
                {
                    "profile": profile,
                    "emoji": emoji.id if hasattr(emoji, "id") else emoji,
                    "label": label,
                    "description": description,
                    "value": value,
                }
                for emoji, label, description, value in reason_options
            ]
            await self.config.guild(ctx.guild).dropdowns.set(dropdowns_config)

    async def check_permissions_in_channel(
        self, permissions: typing.List[str], channel: discord.TextChannel
    ) -> typing.List[str]:
        """Function to checks if the permissions are available in a guild.
        This will return a list of the missing permissions.
        """
        return [
            permission
            for permission in permissions
            if not getattr(channel.permissions_for(channel.guild.me), permission)
        ]

    # @configuration.command(aliases=["buttonembed"])
    # async def embedbutton(
    #     self,
    #     ctx: commands.Context,
    #     profile: ProfileConverter,
    #     where: typing.Literal["title", "description", "image", "placeholderdropdown"],
    #     *,
    #     text: typing.Optional[str] = None,
    # ):
    #     """Set the settings for the button embed."""
    #     if text is None:
    #         if where == "title":
    #             await self.config.guild(ctx.guild).profiles.clear_raw(profile, "embed_button", "title")
    #         elif where == "description":
    #             await self.config.guild(ctx.guild).profiles.clear_raw(profile, "embed_button", "description")
    #         elif where == "image":
    #             await self.config.guild(ctx.guild).profiles.clear_raw(profile, "embed_button", "image")
    #         elif where == "placeholderdropdown":
    #             await self.config.guild(
    #                 ctx.guild
    #             ).profiles.clear_raw(profile, "embed_button", "placeholder_dropdown")

    #         return

    #     if where == "title":
    #         await self.config.guild(ctx.guild).profiles.set_raw(profile, "embed_button", "title", value=text)
    #     elif where == "description":
    #         await self.config.guild(ctx.guild).profiles.set_raw(profile, "embed_button", "description", value=text)
    #     elif where == "image":
    #         await self.config.guild(ctx.guild).profiles.set_raw(profile, "embed_button", "image", value=text)
    #     elif where == "placeholderdropdown":
    #         await self.config.guild(ctx.guild).profiles.set_raw(profile, "embed_button", "placeholder_dropdown", value=text)
