from typing import Literal
import config
from discord import Embed
from virtualcrypto import VirtualCryptoClient, Scope
import pymysql.cursors
import embedColour
from decimal import Decimal

VCClient = VirtualCryptoClient(
    client_id=config.VirtualCrypto.client_id,
    client_secret=config.VirtualCrypto.client_secret,
    scopes=[Scope.Pay, Scope.Claim]
)

def dict_factory(cursor, row):
   d = {}
   for idx, col in enumerate(cursor.description):
       d[col[0]] = row[idx]
   return d

def DBConnection():
    connection = pymysql.connect(host=config.MySQL.HOST,port=config.MySQL.PORT,
                                 user=config.MySQL.USER,password=config.MySQL.PASSWORD,database=config.MySQL.DATABASE,
                                 cursorclass=pymysql.cursors.DictCursor)
    cursor = connection.cursor()
    return connection, cursor

def amount_format(amount:int) -> str:
    return str(f"{amount:,.6f}".strip('0').rstrip('.'))

def swap_estimation(reserve_input_currency:int, reserve_output_currency:int, swap_fee:int, input_amount:int) -> int:
    fee_multiplier = 1000 - swap_fee
    effective_input = (input_amount * fee_multiplier) // 1000
    denominator = reserve_input_currency + effective_input
    if denominator == 0:
        estimated_output_amount = 0
    else:
        estimated_output_amount = (reserve_output_currency * effective_input) // denominator
    return estimated_output_amount

def bot_help() -> list[Embed]:
    embeds = []
    embed = Embed()
    embed.colour = embedColour.LightBlue
    embed.title = "各種コマンド"
    embed.add_field(name="/help",value="主要なコマンドの使い方を表示します",inline=False)
    embed.add_field(name="/info",value="このボットやネットワークに関する情報を表示します",inline=False)
    embed.add_field(name="/swap_info [通貨単位]",value="対象の通貨の流動性プールの情報を取得します",inline=False)
    embed.add_field(name="/swap_history [通貨単位]",value="スワップの履歴を表示します",inline=False)
    embed.add_field(name="/swap_calc [通貨単位] [購入/売却] [入力する数量]",value="スワップ時の計算をシミュレートします",inline=False)
    embed.add_field(name="/swap_exec [通貨単位] [購入/売却] [入力する数量]",value="スワップを実行します\n事前に`/swap_calc`で出力数量を確認しておくことをお勧めします",inline=False)
    embed.add_field(name="/create_liquidly [通貨単位]",value="流動性プールを作成します",inline=False)
    embeds.append(embed)
    embed = Embed()
    embed.colour = embedColour.LightBlue
    embed.title = "注意点"
    embed.add_field(name="流動性プールの作成",value="流動性プールを作成する際は、流通量が1000枚以上の通貨を選択してください\nまた、流通量の50%以上を保有していることを確認してください",inline=False)
    embed.add_field(name="スワップ手数料",value="デフォルトのスワップ手数料は3.0%です",inline=False)
    embed.add_field(name="スワップ価格",value="スワップ価格はプールの残高によって変動します",inline=False)
    embed.add_field(name="スワップ履歴",value="スワップ履歴は最新の5件まで表示されます",inline=False)
    embeds.append(embed)
    return embeds

def bot_info() -> Embed:
    try:
        embed = Embed()
        embed.colour = embedColour.LightBlue
        embed.title = "Info"
        embed.add_field(name="使用しているネットワーク",value="[VirtualCrypto](https://vcrypto.sumidora.com)",inline=False)
        bot_balance_list = VCClient.get_balances()
        bot_base_currency_balance = 0
        for bot_balance in bot_balance_list:
            if bot_balance.currency.unit == config.Swap.base_currency_unit:
                bot_base_currency_balance = bot_balance.amount
                break
        connection, cursor = DBConnection()
        cursor.execute("SELECT COUNT(*) FROM liquidity")
        pool_count = cursor.fetchall()[0]['COUNT(*)']
        cursor.execute("SELECT SUM(reserve_base_currency) FROM liquidity")
        total_base_currency_reserve = cursor.fetchall()[0]['SUM(reserve_base_currency)']
        if not total_base_currency_reserve:
            total_base_currency_reserve = 0
        connection.close()
        embed.add_field(name="流動性プールの数",value=pool_count,inline=False)
        embed.add_field(name="流動性プールの総残高",value=f"{amount_format(total_base_currency_reserve)} {config.Swap.base_currency_unit}",inline=False)
        embed.add_field(name="ボットの残高",value=f"{amount_format(bot_base_currency_balance)} {config.Swap.base_currency_unit}",inline=False)
        embed.add_field(name="ボットの招待",value="[ボットをサーバーに招待する](https://discord.com/oauth2/authorize?client_id=1343234370525200505&permissions=2147552256&integration_type=0&scope=bot)",inline=False)
        embed.add_field(name="サポートサーバー",value="https://discord.gg/wDmkHthbaU",inline=False)
        embed.add_field(name="作成者",value="h4ribote",inline=False)
        return embed
    except Exception as e:
        print(e)
        return Embed(title="Error",description="内部エラー",color=embedColour.Error)

def swap_info(pair_currency_unit:str) -> Embed:
    connection, cursor = DBConnection()
    cursor.execute("SELECT * FROM liquidity WHERE pair_currency_unit = %s",(pair_currency_unit,))
    pool_data = cursor.fetchall()
    connection.close()
    if not pool_data:
        return Embed(title="Error",description="Swap pair not found",color=embedColour.Error)
    pool_data = pool_data[0]
    response_embed = Embed(title=f"{pair_currency_unit}/{config.Swap.base_currency_unit}",color=embedColour.LightBlue)
    response_embed.add_field(name=f"プール残高({pair_currency_unit})",value=amount_format(pool_data['reserve_pair_currency']),inline=False)
    response_embed.add_field(name=f"プール残高({config.Swap.base_currency_unit})",value=amount_format(pool_data['reserve_base_currency']),inline=False)
    response_embed.add_field(name="スワップ手数料",value=f"{pool_data['swap_fee']/10}%",inline=False)

    estimated_input = int(pool_data['reserve_pair_currency']) // 4 + 5
    estimated_output_amount = swap_estimation(int(pool_data['reserve_pair_currency']),int(pool_data['reserve_base_currency']),int(pool_data['swap_fee']),estimated_input)
    estimated_price = estimated_output_amount / estimated_input

    response_embed.add_field(name="推定価格",value=f"1 {pair_currency_unit} = {amount_format(estimated_price)} {config.Swap.base_currency_unit}",inline=False)
    return response_embed

def swap_history(currency_unit:str) -> list[Embed]:
    connection, cursor = DBConnection()
    cursor.execute("SELECT * FROM swap_history WHERE pair_currency_unit = %s",(currency_unit,))
    history_data = cursor.fetchall()
    connection.close()
    if not history_data:
        return [Embed(title="Error",description="History not found",color=embedColour.Error)]
    response_embeds = []
    for history in history_data:
        response_embed = Embed(title=f"{history['pair_currency_unit']}/{config.Swap.base_currency_unit}")
        response_embed.add_field(name="スワップタイプ",value=history['swap_type'],inline=False)
        if history['swap_type'] == "buy":
            response_embed.colour = embedColour.InTx
            response_embed.add_field(name="入力数量",value=f"{amount_format(history['input_amount'])} {config.Swap.base_currency_unit}",inline=False)
            response_embed.add_field(name="出力数量",value=f"{amount_format(history['output_amount'])} {currency_unit}",inline=False)
            response_embed.add_field(name="取引価格",value=f"1 {currency_unit} = {amount_format(history['input_amount']/history['output_amount'])} {config.Swap.base_currency_unit}",inline=False)
        else:
            response_embed.colour = embedColour.OutTx
            response_embed.add_field(name="入力数量",value=f"{amount_format(history['input_amount'])} {currency_unit}",inline=False)
            response_embed.add_field(name="出力数量",value=f"{amount_format(history['output_amount'])} {config.Swap.base_currency_unit}",inline=False)
            response_embed.add_field(name="取引価格",value=f"1 {currency_unit} = {amount_format(history['output_amount']/history['input_amount'])} {config.Swap.base_currency_unit}",inline=False)
        response_embed.add_field(name="スワップ日時",value=f"<t:{history['timestamp']}:f>",inline=False)
        response_embeds.append(response_embed)
        if len(response_embeds) >= 5:
            break
    return response_embeds

def swap_calc(pair_currency_unit:str, swap_type:Literal['buy','sell'], input_amount:int) -> Embed:
    connection, cursor = DBConnection()
    cursor.execute("SELECT * FROM liquidity WHERE pair_currency_unit = %s",(pair_currency_unit,))
    pool_data = cursor.fetchall()
    connection.close()
    if not pool_data:
        return Embed(title="Error",description="Pool not found",color=embedColour.Error)
    pool_data = pool_data[0]
    if swap_type == "buy":
        estimated_output_amount = swap_estimation(int(pool_data['reserve_base_currency']),int(pool_data['reserve_pair_currency']),int(pool_data['swap_fee']),input_amount)
    else:
        estimated_output_amount = swap_estimation(int(pool_data['reserve_pair_currency']),int(pool_data['reserve_base_currency']),int(pool_data['swap_fee']),input_amount)
    response_embed = Embed(title=f"{pair_currency_unit}/{config.Swap.base_currency_unit}",color=embedColour.LightBlue)
    if swap_type == "buy":
        response_embed.add_field(name="入力数量",value=f"{amount_format(input_amount)} {config.Swap.base_currency_unit}",inline=False)
        response_embed.add_field(name="出力数量",value=f"{amount_format(estimated_output_amount)} {pair_currency_unit}",inline=False)
        estimated_price = input_amount / estimated_output_amount
        response_embed.add_field(name="推定価格",value=f"1 {pair_currency_unit} = {amount_format(estimated_price)} {config.Swap.base_currency_unit}",inline=False)
    else:
        response_embed.add_field(name="入力数量",value=f"{amount_format(input_amount)} {pair_currency_unit}",inline=False)
        response_embed.add_field(name="出力数量",value=f"{amount_format(estimated_output_amount)} {config.Swap.base_currency_unit}",inline=False)
        estimated_price = estimated_output_amount / input_amount
        response_embed.add_field(name="推定価格",value=f"1 {pair_currency_unit} = {amount_format(estimated_price)} {config.Swap.base_currency_unit}",inline=False)
    return response_embed

def swap_exec(user_id:int,pair_currency_unit:str, swap_type:Literal['buy','sell'], input_amount:int) -> Embed:
    try:
        connection, cursor = DBConnection()
        cursor.execute("SELECT * FROM liquidity WHERE pair_currency_unit = %s",(pair_currency_unit,))
        pool_data = cursor.fetchall()
        connection.close()
        if not pool_data:
            return Embed(title="Error",description="Pool not found",color=embedColour.Error)
        if swap_type == "buy":
            claim_id = VCClient.create_claim(user_id,config.Swap.base_currency_unit,input_amount,{"type":"buy","currency_unit":pair_currency_unit}).id
        else:
            claim_id = VCClient.create_claim(user_id,pair_currency_unit,input_amount,{"type":"sell","currency_unit":pair_currency_unit}).id
        return Embed(title="Success",description=f"請求`{claim_id}`が作成されました",color=embedColour.Yellow)
    except Exception as e:
        print(e)
        return Embed(title="Error",description="内部エラー",color=embedColour.Error)

def create_liquidly(user_id:int,pair_currency_unit:str) -> Embed:
    try:
        if pair_currency_unit == config.Swap.base_currency_unit:
            return Embed(title="Error",description="Invalid currency",color=embedColour.Error)
        connection, cursor = DBConnection()
        cursor.execute("SELECT * FROM liquidity WHERE pair_currency_unit = %s",(pair_currency_unit,))
        pool_data = cursor.fetchall()
        cursor.execute("SELECT SUM(reserve_base_currency) FROM liquidity")
        total_base_currency_reserve = cursor.fetchall()[0]['SUM(reserve_base_currency)']
        if not total_base_currency_reserve:
            total_base_currency_reserve = 0
        connection.close()
        if pool_data:
            return Embed(title="Error",description="入力された通貨のペアは既に存在します",color=embedColour.Error)
        bot_base_currency_balance = 0
        bot_balance_list = VCClient.get_balances()
        for bot_balance in bot_balance_list:
            if bot_balance.currency.unit == config.Swap.base_currency_unit:
                bot_base_currency_balance = bot_balance.amount
                break
        initial_base_reserve = config.Swap.initial_base_reserve
        if (bot_base_currency_balance - total_base_currency_reserve) < initial_base_reserve:
            return Embed(title="Error",description="ボットの残高(vcl)が不足しています",color=embedColour.Error)
        pair_currency_circulation = VCClient.get_currency_by_unit(pair_currency_unit).total_amount
        if not pair_currency_circulation:
            return Embed(title="Error",description="通貨が存在しません",color=embedColour.Error)
        if pair_currency_circulation < 1000:
            return Embed(title="Error",description="流通量が1000枚以上の通貨を選択する必要があります",color=embedColour.Error)
        claim_amount = pair_currency_circulation // 2
        claim_id = VCClient.create_claim(user_id,pair_currency_unit,claim_amount,{"type":"deposit","currency_unit":pair_currency_unit}).id
        return Embed(title="Success",description=f"請求`{claim_id}`が作成されました",color=embedColour.Yellow)
    except Exception as e:
        print(e)
        return Embed(title="Error",description="内部エラー",color=embedColour.Error)

def available_currency() -> Embed:
    connection, cursor = DBConnection()
    cursor.execute("SELECT * FROM liquidity LIMIT 100")
    pair_data = cursor.fetchall()
    connection.close()
    if not pair_data:
        return Embed(title="Error",description="有効な通貨ペアが存在しません\n`/create_liquidly`から新たな流動性プールを作成してください",color=embedColour.Error)
    response_embed = Embed(title="取引可能な通貨ペアの一覧(+預け入れ数量)",description="最大100件まで表示",color=embedColour.LightBlue)
    for pair in pair_data:
        response_embed.add_field(name=f"{pair['pair_currency_unit']}/{config.Swap.base_currency_unit}",value=f"{amount_format(pair['reserve_pair_currency'])} {pair['pair_currency_unit']}",inline=False)
    return response_embed
