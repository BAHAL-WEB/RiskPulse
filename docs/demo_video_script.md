# Demo video script (about 9 minutes, screen recording)

Record with any screen recorder, upload to YouTube as **Unlisted**, and paste the link into the README.

**Before you record:** run `python app.py` once to check it works; try **Live headlines** and note which feeds respond. If your network blocks them, say so on camera and use the sample data. Increase the browser zoom and terminal font so they are readable.

## 1. Intro (0:00 to 0:45)

**On screen:** Slide 1 of docs/presentation.pdf, then the README.

**Say:**

> Hi, I'm [your name], and this is RiskPulse, my submission for the AI/NLP Risk Engine case study. I chose Module B, strategic portfolio stress testing.

> The problem is simple. News moves markets faster than a risk team can turn it into numbers. By the time someone has worked out what a headline means for the portfolio, the market has already moved.

> RiskPulse closes that gap. It reads news and social posts, scores each one for sentiment, event type and market impact, and when the impact is high, it automatically stress tests a synthetic wholesale banking portfolio and tells you whether you have breached your loss limits.

## 2. Architecture (0:45 to 1:45)

**On screen:** docs/architecture.png. Point at each box as you mention it.

**Say:**

> Here is the architecture, left to right.

> On the left are two kinds of sources: news, from live RSS feeds of news channels, GDELT or files, and social posts in the style of Twitter or X. The ingestion layer converts both into one common document format.

> Next is the NLP Risk Engine, the core of the project. For every document it outputs three things: a sentiment score from minus one to one, an event class like Geopolitical or Credit Event, and an impact score from one to ten. Those are written to a signals file and also exposed through a small web API, so any downstream module can use them.

> Then Module B takes over. Any signal with an impact above a sensitivity level, seven by default, triggers a stress test. The event class picks the shock set, the impact score scales how hard it hits, and the portfolio, shown here at the bottom, is revalued. The result goes to the app.

## 3. Launch the app (1:45 to 2:30)

**On screen:** Terminal: run python app.py. The browser opens on the Stress tests tab with Sample data selected.

**Say:**

> To run it, one command: python app.py. There are no installs and no API keys, it uses only the Python standard library.

> The app opens on the bundled sample data. The headline at the top tells me in plain English what is going on: 6 of 23 headlines look serious enough to stress-test the 3.98 billion dollar portfolio, the worst case is a loss of 349 million dollars, and two scenarios breach the loss limit.

> The Sensitivity slider next to it controls how serious a headline has to be before it triggers a stress test.

## 4. Live headlines (2:30 to 3:45)

**On screen:** Click Live headlines. Wait for the toast. Point at the status line, then click feed details.

**Say:**

> The case study asks for real-time data, so let me switch to live headlines. This pulls the latest headlines from public RSS feeds of news channels, such as BBC, the New York Times, the Guardian, the Wall Street Journal and Bloomberg, plus GDELT. No API key is needed.

> The status line shows how many headlines came in and from how many feeds. If a feed is down it is skipped, and feed details shows exactly which ones worked.

> The summary has now updated to today's news. On a quiet day nothing may pass the sensitivity level, and the app says so and offers to lower it. I can also hit Refresh at any time to pull the latest headlines. The feed list is just a JSON file, so adding another news source takes one line.

## 5. From text to signal (3:45 to 5:00)

**On screen:** Headlines tab. Click a high-impact row to open Why this score.

**Say:**

> The Headlines tab lists everything the engine scored. I can search, and filter by event type or source.

> If I click a headline, the app explains the score in plain English. For example, a bank collapse is classed as a Credit Event, which starts at a base severity of 6.5. Strongly negative tone adds about 2.3, and severity words like collapse add 1.2, which gives an impact of ten. A risk reviewer can see exactly why it scored that way.

> The sentiment uses a finance-specific lexicon with negation handling, so 'not weak' scores better than 'weak'. If you want a neural model, there is a flag to swap in FinBERT.

## 6. The stress test (5:00 to 6:45)

**On screen:** Stress tests tab. Select the Geopolitical event, then the Credit Event, then the Macroeconomic event.

**Say:**

> Back on Stress tests. On the left are the triggered events with their loss and a Warning or Breach label. On the right is the detail.

> For the Taiwan story, the box at the top says in words what it means: the loss is beyond the 2.5 percent early-warning level. Portfolio value goes from 3,975 million to about 3,789 million, a loss of 186 million. The bar shows where that sits against the warning and breach limits.

> Below are the market shocks we assumed, and charts by asset type, by risk driver, by sector and by region. Now the credit event: it is a bigger loss and a breach, driven mostly by credit spreads. For the macro event, the main driver is interest rates, because bond prices fall when yields rise, and pay-fixed swaps in the book partly offset that.

> At the bottom is the list of the largest individual losses, so a risk manager knows which trades to look at first. Now I'll move the Sensitivity slider down to five: more headlines now trigger tests, and the summary updates instantly.

## 7. Analyze your own and what-if (6:45 to 8:00)

**On screen:** Analyze your own tab: click an example, press Analyze, then Run what-if on this. Then What-if scenario tab: click the Taiwan crisis preset.

**Say:**

> I can also try my own text. Here I paste a headline, or click one of the examples, and press Analyze. I get the tone, the event type with a confidence, the impact meter, and the same plain-English explanation. If it was a tweet, I choose Social post, which is how social text can be brought in.

> Run what-if on this takes that event, its region and severity straight into a stress test. The What-if tab also lets me build a scenario from scratch, or use a preset like Taiwan crisis, without waiting for the news. This is useful for planning, not just reacting.

## 8. Tests, limitations and wrap-up (8:00 to 9:00)

**On screen:** Terminal: run python -m unittest. Then slide 7 of the deck.

**Say:**

> Behind the app there are 20 automated tests. They check that sentiment moves in the right direction, that events are classified correctly, that the stress P&L reconciles exactly to before and after values, that a pay-fixed swap gains when rates rise, that the live feed parser handles RSS and Atom and survives a broken feed, and that the web API validates input. They all pass.

> To be honest about the limits: the NLP is rule-based, so it will miss sarcasm and unusual phrasing, and real headlines are short, so many score low. The best next step is fine-tuning on the Kaggle financial news and tweet datasets behind the same output format. The shock sizes are assumptions, not calibrated to history, the pricing is first-order, and the portfolio is synthetic. This is a prototype, not a regulatory capital model.

> What it does show is a complete, explainable pipeline from live news to a limit-checked loss estimate in seconds. The code, deck and data are all in the GitHub repo linked in the description. Thanks for watching.

## Recording tips

- Narration is about 1,200 words, which fits 9 to 10 minutes at a relaxed pace.
- If you run short, cut section 7. If you run long, shorten the macro comparison in section 6.
- Live headlines depend on the day's news and your network. Try it right before recording.
- Upload as Unlisted on YouTube, then paste the link into the README.
