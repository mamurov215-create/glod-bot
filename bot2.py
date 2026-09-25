//@version=5
indicator("SMC BUY SELL Mobil & Bot", overlay=true, max_labels_count=100, max_lines_count=50)

// --- SOZLAMALAR ---
swingLen  = input.int(5, "Swing uzunligi", minval=2, group="Asosiy sozlamalar")
emaLen    = input.int(200, "Trend EMA", group="Asosiy sozlamalar")
useVol    = input.bool(true, "Hajm filtri", group="Filtrlar")
useRsi    = input.bool(true, "RSI filtri", group="Filtrlar")
onlyChoch = input.bool(false, "Faqat CHoCH (Struktura o'zgarishi)", group="Filtrlar")
slMult    = input.float(1.5, "SL (ATR x)", step=0.1, group="Risk boshqaruvi")
rr        = input.float(2.0, "Risk:Reward (TP)", step=0.5, group="Risk boshqaruvi")
cool      = input.int(5, "Pauza (shamlar)", group="Boshqaruv")

// --- HISOBLashlar ---
atr = ta.atr(14)
ema = ta.ema(close, emaLen)
rsi = ta.rsi(close, 14)

var float lastHigh = na
var float lastLow = na
var bool hCrossed = false
var bool lCrossed = false
var int trend = 0
var int lastSig = na
var float tpLevel = na
var float slLevel = na

ph = ta.pivothigh(high, swingLen, swingLen)
pl = ta.pivotlow(low, swingLen, swingLen)

lastHigh := not na(ph) ? ph : lastHigh
hCrossed := not na(ph) ? false : hCrossed
lastLow  := not na(pl) ? pl : lastLow
lCrossed := not na(pl) ? false : lCrossed

bullBrk = not na(lastHigh) and not hCrossed and ta.crossover(close, lastHigh)
bearBrk = not na(lastLow) and not lCrossed and ta.crossunder(close, lastLow)

prev = trend
hCrossed := bullBrk ? true : hCrossed
lCrossed := bearBrk ? true : lCrossed
trend    := bullBrk ? 1 : bearBrk ? -1 : trend

volOk  = not useVol or na(volume) or volume > ta.sma(volume, 20) * 1.2
bodyOk = math.abs(close - open) > atr * 0.5
coolOk = na(lastSig) or bar_index - lastSig >= cool

buyB  = onlyChoch ? (bullBrk and prev == -1) : bullBrk
sellB = onlyChoch ? (bearBrk and prev == 1) : bearBrk

buy   = buyB and close > ema and (not useRsi or (rsi > 50 and rsi < 78)) and volOk and bodyOk and coolOk and barstate.isconfirmed
sell  = sellB and close < ema and (not useRsi or (rsi < 50 and rsi > 22)) and volOk and bodyOk and coolOk and barstate.isconfirmed

sig     = buy or sell
d       = buy ? 1 : -1
lastSig := sig ? bar_index : lastSig
slLevel := sig ? close - d * atr * slMult : slLevel
tpLevel := sig ? close + d * atr * slMult * rr : tpLevel

// --- GRAFIKGA CHIZISH ---
plot(ema, "EMA Trend", color=color.new(color.gray, 40))
plot(tpLevel, "Take Profit (TP)", color=color.green, style=plot.style_linebr)
plot(slLevel, "Stop Loss (SL)", color=color.red, style=plot.style_linebr)

plotshape(buy, "BUY", shape.labelup, location.belowbar, color=color.new(#089981, 0), text="BUY", textcolor=color.white, size=size.normal)
plotshape(sell, "SELL", shape.labeldown, location.abovebar, color=color.new(#F23645, 0), text="SELL", textcolor=color.white, size=size.normal)

// --- TELEGRAM BOT UCHUN ALERT (OGOHLANTIRISH) SHARTLARI ---
alertcondition(buy, title="BUY Signal", message="🟢 SOTIB OLISH (BUY) signali keldi!")
alertcondition(sell, title="SELL Signal", message="🔴 SOTISH (SELL) signali keldi!")
