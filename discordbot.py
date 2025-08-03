import discord
import os
from dotenv import load_dotenv
from discord import option
from discord.ext import commands

load_dotenv()
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

def implied_prob(odds):
    return -odds / (-odds + 100) if odds < 0 else 100 / (odds + 100)

def fair_value(fv_odds):
    probs = [implied_prob(od) for od in fv_odds]
    true_prob = 1
    for p in probs:
        true_prob *= p
    return true_prob

def fair_val_odds(prob):
    if prob == 1:
        return float('inf')
    return round((100 / prob) - 100) if prob < 0.5 else round(-(100 * prob) / (1 - prob))

def expected_value(payout_odds, fv_odds, boost=0):
    final_odds = payout_odds + boost
    win_prob = fair_value(fv_odds)
    decimal_odds = (final_odds / 100) + 1 if final_odds > 0 else (100 / -final_odds) + 1
    ev = ((decimal_odds * win_prob) - 1) * 100
    fair_val = fair_val_odds(win_prob)
    return round(ev, 1), round(win_prob * 100, 1), fair_val

def kelly_stakes(bankroll=100, ev=0.36, win_prob=0.136):
    b = (1 + ev / 100)
    k = (b * win_prob - (1 - win_prob)) / b
    k = max(k, 0)
    units = [1, 0.5, 0.25, 0.125]
    returns = []
    for u in units:
        stake = round(k * bankroll * u, 2)
        payout = round(stake * (1 + ev / 100), 2)
        returns.append((stake, payout))
    return returns

@bot.event
async def on_ready():
    print(f"{bot.user} is ready!")

@bot.slash_command(name="ev", description="Use Probit devigging to get the EV of a bet.")
@option("payout_odds", description="The odds of the bet.")
@option("fv_odds", description="The fair value odds of each leg (comma separated).")
@option("boost", description="[optional] Boost to add to the odds.", required=False)
@option("bet_name", description="[optional] Name of the bet.", required=False)
async def ev(ctx, payout_odds: int, fv_odds: str, boost: int = 0, bet_name: str = "Unnamed Bet"):
    try:
        odds_list = [int(o.strip()) for o in fv_odds.split(",")]
        ev_pct, win_prob, fair_val = expected_value(payout_odds, odds_list, boost)
        kelly_lines = kelly_stakes(ev=ev_pct, win_prob=win_prob / 100)

        embed = discord.Embed(
            title=f"📊 {bet_name}",
            description="**EV Calc (Probit)** ✅",
            color=0xf97316
        )
        embed.add_field(name="Input", value=f"Payout: {payout_odds}\nFV Odds: {fv_odds}", inline=False)
        embed.add_field(name="Result", value=f"%EV: {ev_pct}%\nWinProb: {win_prob}%\nFairVal: +{fair_val}", inline=False)

        kelly_text = ""
        labels = ["Full", "1/2", "1/4", "1/8"]
        for i, (stake, payout) in enumerate(kelly_lines):
            kelly_text += f"{labels[i]}: {stake:.2f}u -> {payout:.2f}u\n"

        embed.add_field(name="Kelly Values / Return", value=kelly_text, inline=False)

        await ctx.respond(embed=embed)
    except Exception as e:
        await ctx.respond(f"⚠️ Error: {str(e)}")

bot.run(os.getenv('TOKEN'))
