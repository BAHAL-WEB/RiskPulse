"""Finance-tuned lexicons and rule tables (kept in code so the engine runs offline)."""

POSITIVE = {
    "beat": 2, "beats": 2, "surge": 2, "surges": 2, "soar": 2, "soars": 2, "rally": 2,
    "record": 1.5, "growth": 1, "strong": 1.5, "upgrade": 2, "upgraded": 2, "gain": 1,
    "gains": 1, "profit": 1, "profits": 1, "outperform": 2, "boost": 1.5, "recovery": 1.5,
    "resilient": 1.5, "expansion": 1, "approve": 1, "approved": 1, "innovative": 1,
    "breakthrough": 2, "optimism": 1.5, "bullish": 2, "ease": 1, "eases": 1,
    "launch": 0.5, "launches": 0.5, "unveils": 0.5, "partnership": 1, "win": 1.5,
    "wins": 1.5, "steady": 1, "rises": 1, "jumps": 0.5, "climbs": 1, "rebounds": 1.5, "cooling": 0.5, "exceeds": 2, "improves": 1, "stabilise": 1, "stabilize": 1,
}

NEGATIVE = {
    "miss": -2, "misses": -2, "plunge": -3, "plunges": -3, "collapse": -3, "collapses": -3,
    "default": -3, "defaults": -3, "bankruptcy": -3, "bankrupt": -3, "downgrade": -2,
    "downgraded": -2, "loss": -1.5, "losses": -1.5, "fraud": -3, "crash": -3, "slump": -2,
    "sanction": -2, "sanctions": -2, "war": -3, "invasion": -3, "missile": -2.5,
    "escalate": -2, "escalates": -2, "escalation": -2, "tensions": -1.5, "probe": -1.5,
    "lawsuit": -1.5, "layoffs": -2, "recession": -3, "inflation": -1, "tumble": -2,
    "tumbles": -2, "breach": -2.5, "hack": -2.5, "hacked": -2.5, "ransomware": -3,
    "shortage": -1.5, "warning": -1.5, "warns": -1.5, "fear": -1.5, "fears": -1.5,
    "selloff": -2.5, "sell-off": -2.5, "turmoil": -2.5, "crisis": -3, "contagion": -3,
    "bearish": -2, "weak": -1.5, "cuts": -1, "halt": -2, "halts": -2, "freeze": -2,
    "blockade": -3, "earthquake": -2.5, "flood": -2, "hurricane": -2.5, "outage": -2,
    "fine": -1, "fined": -1.5, "writedown": -2, "write-down": -2, "distress": -2.5,
    "shock": -2, "surprise": -0.5, "hike": -1, "hikes": -1, "bailout": -2.5,
    "panic": -2.5, "attack": -2.5, "attacks": -2.5, "strikes": -1.5, "bomb": -3, "bombing": -3, "killed": -2.5,
    "deaths": -2.5, "retaliation": -2, "collapses": -3, "shutdown": -2, "looms": -1.5, "tumbled": -2, "slumps": -2, "plummets": -3,
    "plummet": -3, "wipes": -2, "fails": -2, "rush": -1, "stress": -1, "disruption": -2, "disruptions": -2,
}

NEGATORS = {"not", "no", "never", "without", "fails", "failed", "unlikely", "denies", "avoids", "averts"}
INTENSIFIERS = {"sharply": 1.4, "massive": 1.4, "severe": 1.4, "huge": 1.3, "major": 1.2,
                "unprecedented": 1.5, "significantly": 1.3, "heavy": 1.2}

# event_type -> {regex: weight}
EVENT_RULES = {
    "Geopolitical": {
        r"\b(war|invasion|missile|military|troops|blockade|sanctions?|embargo|tariffs?|"
        r"tensions?|conflict|ceasefire|nato|coup|strait|border|airstrikes?|diplomatic|attacks?|strikes|offensive|"
        r"retaliat\w+|shelling|bomb\w*|drones?|hostages?|nuclear|annex\w*|escalat\w+|war)\b": 2.0,
        r"\b(election|geopolitic\w*|summit|treaty|trade war)\b": 1.0,
    },
    "Macroeconomic": {
        r"\b(inflation|cpi|gdp|recession|unemployment|jobs report|rate (hike|cut|decision)|"
        r"interest rates?|central bank|federal reserve|fed|ecb|rbi|yield curve|"
        r"monetary policy|payrolls|stagflation|bond yields?|retail sales|consumer spending|consumer prices?|"
        r"manufacturing|pmi|trade deficit|economy|economic|budget|shutdown|debt ceiling|fiscal|"
        r"bank of england|boe|boj|treasury yields?|rates?)\b": 2.0,
        r"\b(treasury|dollar|oil prices?|commodit\w+)\b": 1.0,
    },
    "Credit Event": {
        r"\b(default|defaults|bankruptcy|bankrupt|insolvency|downgrade[ds]?|junk|"
        r"restructur\w+|bailout|liquidity crunch|bank run|credit rating|covenant|"
        r"write-?down|non-performing|distress\w*|creditors?|chapter 11|collaps\w+|bank failure|"
        r"depositors?|rush to withdraw|insolven\w+|fails?|rescue)\b": 2.2,
        r"\b(debt|bond spreads?|cds|credit)\b": 0.8,
    },
    "Merger/Acquisition": {
        r"\b(acquire[sd]?|acquisition|merger|merge[sd]?|takeover|buyout|"
        r"to buy|bid for|stake in|divest\w*|spin-?off|antitrust approval)\b": 2.5,
        r"\b(deal|offer|billion)\b": 0.4,
    },
    "Product Launch": {
        r"\b(unveil\w*|rolls? out|introduces?|debut\w*|launch\w* (a |an |its |the )?(new|latest|first)|"
        r"new product|new model|new platform|new service)\b": 2.2,
        r"\b(launch(es|ed)?|releases?)\b": 0.8,
        r"\b(innovation|prototype|beta)\b": 0.8,
    },
    "Regulatory": {
        r"\b(regulator\w*|sec|fine[sd]?|antitrust|compliance|investigation|probe|"
        r"lawsuit|ban[sn]?|legislation|subpoena|doj|ftc|sebi|basel|penalt\w+)\b": 2.0,
    },
    "Cyber/Operational": {
        r"\b(cyber\w*|hack\w*|data breach|breach|ransomware|outage|systems? down|"
        r"malware|ddos|supply chain disruption|strike|recall)\b": 2.4,
    },
    "Natural Disaster": {
        r"\b(earthquake|hurricane|typhoon|flood\w*|wildfire|tsunami|cyclone|"
        r"drought|natural disaster|storm)\b": 2.6,
    },
    "Earnings": {
        r"\b(earnings|quarterly results|revenue|eps|guidance|profit|net income|"
        r"beats? estimates|misses? estimates|q[1-4])\b": 1.8,
    },
}

# Base market severity for each event class (1-10). Tuned for wholesale-banking relevance.
BASE_IMPACT = {
    "Geopolitical": 6.5, "Macroeconomic": 6.0, "Credit Event": 6.5,
    "Merger/Acquisition": 4.0, "Product Launch": 2.5, "Regulatory": 4.5,
    "Cyber/Operational": 5.5, "Natural Disaster": 5.5, "Earnings": 3.5, "Other": 2.0,
}

SEVERITY_TERMS = {
    r"\b(war|invasion|missile|blockade|default|bankruptcy|collapse|crisis|contagion|"
    r"bank run|bailout|ransomware|systemic|meltdown|emergency)\b": 1.2,
    r"\b(unprecedented|largest|worst|historic|sharply|plunge[sd]?|crash\w*|panic)\b": 0.8,
    r"\b(global|worldwide|nationwide|multiple (banks|countries)|major)\b": 0.5,
}

COMPANIES = {
    "JPMorgan": "JPM", "Goldman Sachs": "GS", "Citigroup": "C", "Bank of America": "BAC",
    "Morgan Stanley": "MS", "Wells Fargo": "WFC", "HSBC": "HSBC", "Deutsche Bank": "DB",
    "Credit Suisse": "CS", "Apple": "AAPL", "Microsoft": "MSFT", "Amazon": "AMZN",
    "Alphabet": "GOOGL", "Google": "GOOGL", "Meta": "META", "Tesla": "TSLA",
    "Nvidia": "NVDA", "TSMC": "TSM", "Exxon": "XOM", "Chevron": "CVX", "Boeing": "BA",
    "Pfizer": "PFE", "Walmart": "WMT", "Reliance": "RELIANCE.NS", "Infosys": "INFY",
    "Tata": "TTM", "HDFC": "HDB", "Evergrande": "EVGRY", "Intel": "INTC", "Disney": "DIS",
}

REGIONS = {
    "North America": [r"\bu\.?s\.?\b", r"united states", r"america\w*", r"wall street", r"canada", r"federal reserve", r"\bfed\b", r"florida|texas|california|new york|washington|white house|congress"],
    "Europe": [r"europe\w*", r"\becb\b", r"russia\w*", r"ukrain\w*", r"germany", r"\buk\b", r"britain", r"eurozone", r"\bnato\b", r"bank of england|england|london|paris|france|italy|spain|brussels"],
    "Asia": [r"china|chinese", r"taiwan", r"japan\w*", r"hong kong", r"korea\w*", r"singapore", r"asia\w*", r"\bpboc\b"],
    "India": [r"india\w*", r"\brbi\b", r"mumbai", r"sensex", r"nifty"],
    "Middle East": [r"middle east", r"iran\w*", r"israel\w*", r"saudi", r"gulf", r"red sea", r"hormuz", r"\bopec\b"],
    "Latin America": [r"brazil\w*", r"mexic\w*", r"argentin\w*", r"latin america"],
    "Africa": [r"africa\w*", r"nigeria\w*", r"south africa"],
}
