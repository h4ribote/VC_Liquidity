import discord
from discord import app_commands
import bot_commands as cmds
import config
from typing import Literal

client = discord.Client(intents=discord.Intents.default())
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    print(f'" {client.user} "としてログイン中')
    await client.change_presence(activity=discord.Game(name="Amazing Bot by h4ribote"),status=discord.Status.online)
    await tree.sync()

@client.event
async def on_message(message:discord.Message):
    if message.content.startswith(f"<@{client.user.id}>") and message.author.id in config.Discord.ADMIN:
        if message.content.split(' ')[1] == "kill":
            await client.close()
            await client._connection.close()
            exit()

@tree.command(name="help",description="主要なコマンドの使い方を表示します")
@app_commands.allowed_installs(True,True)
async def help_command(interaction:discord.Interaction):
    await interaction.response.defer(thinking=True)
    await interaction.followup.send(embeds=cmds.bot_help())

@tree.command(name="info",description="このボットやネットワークに関する情報を表示します")
@app_commands.allowed_installs(True,True)
async def info_command(interaction:discord.Interaction):
    await interaction.response.defer(thinking=True)
    await interaction.followup.send(embed=cmds.bot_info())

@tree.command(name="swap_info",description="対象の通貨の流動性プールの情報を取得します")
@app_commands.allowed_installs(True,True)
@app_commands.describe(unit="通貨単位")
async def pool_info_command(interaction:discord.Interaction, unit:str):
    await interaction.response.defer(thinking=True)
    await interaction.followup.send(embed=cmds.swap_info(unit))

@tree.command(name="swap_history",description="スワップの履歴を表示します")
@app_commands.allowed_installs(True,True)
@app_commands.describe(unit="通貨単位")
async def swap_history_command(interaction:discord.Interaction, unit:str):
    await interaction.response.defer(thinking=True)
    await interaction.followup.send(embeds=cmds.swap_history(unit))

@tree.command(name="swap_calc",description="スワップ時の計算をシミュレートします")
@app_commands.allowed_installs(True,True)
@app_commands.describe(unit="通貨単位",swap_type="購入/売却",input_amount="入力する数量")
async def swap_calc_command(interaction:discord.Interaction, unit:str, swap_type:Literal['buy','sell'], input_amount:int):
    await interaction.response.defer(thinking=True)
    await interaction.followup.send(embed=cmds.swap_calc(unit,swap_type,input_amount))

@tree.command(name="swap_exec",description="スワップを実行します")
@app_commands.allowed_installs(True,True)
@app_commands.describe(unit="通貨単位",swap_type="購入/売却",input_amount="入力する数量")
async def swap_calc_command(interaction:discord.Interaction, unit:str, swap_type:Literal['buy','sell'], input_amount:int):
    await interaction.response.defer(thinking=True)
    await interaction.followup.send(embed=cmds.swap_exec(interaction.user.id,unit,swap_type,input_amount))

@tree.command(name="create_liquidly",description="スワップペアを作成して入金します")
@app_commands.allowed_installs(True,True)
@app_commands.describe(unit="通貨単位")
async def create_liquidly_command(interaction:discord.Interaction, unit:str):
    await interaction.response.defer(thinking=True)
    await interaction.followup.send(embed=cmds.create_liquidly(interaction.user.id,unit))

client.run(config.Discord.BOT_TOKEN)
