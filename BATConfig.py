#Settings for project kept here

#Pusher (live bid updates) - came from BAT page source through chrome network connections
PUSHER_KEY="dea479875ad558950918"
PUSHER_ClUSTER="us3"

#BAT API
HEADERS={"User-Agent": "Mozilla/5.0"}
AUCTIONS_URL="https://bringatrailer.com/auctions"
KEYWORD_API="https://bringatrailer.com/wp-json/bringatrailer/1.0/data/keyword-filter"

#User agent for playwright browser
BROWSER_USER_AGENT=(
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome 120.0.0.0 Safari 537.36"
)

#Percentage above/below average that is bad/good deal
DEAL_THRESHOLD=10
