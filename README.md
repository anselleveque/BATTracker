#**BATTracker**
A car auction tracker for website bringatrailer.com.
The current scope of this project is to create a live tracking program for car auctions, as well as checking their prices against historical averages.
In addition, there will be an element that has a deep dive into a single car, and using bayesian hedonic pricing, will attempt to statistically analyze the price of the car and compare it against the expected price.

##**Main Tracker**
To run the main tracker, run main.py, it will usually run showing the auctions ending within the day 
If you want something different then you can change the seconds=86400 in the function run at the bottom of the page

For inputs, first put models (Porsche,BMW,Honda, etc), then models (911,M3,Civic Si,etc), then any extra keywords.
Keywords will be dropped first, so use them as extra qualifiers (6-speed,manual,10k-miles,etc)

##**Deep Dive**
To run the deep dive, run deep_dive.py and input the URL of the car you want to analyze
It will look at the titles of all previous sales and predict a price of the car, with a 90% interval in addition

##**Future Plans**
Future plans are to further improve the bayesian process, going deeper into the condition of the car and the qualifiers that change its value

