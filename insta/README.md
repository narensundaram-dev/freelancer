# Client Requirement:

Go to Instagram, click search and then select 'TAGS' and then write #STREETBRAND and go through profiles of the last 500 posts
in the 'RECENT' section.


#### You must collect this information from their instagram page. ####

- INSTAGRAM USERNAME
- FOLLOWER COUNT
- GENDER 
- CITY (IF DISPLAYED)
- EMAIL ADDRESS (IF DISPLAYED)
- PHONE NUMBER (IF DISPLAYED)


# Setup:

- Install chrome-driver(for your chrome version) from https://chromedriver.chromium.org/downloads
- Extract the downloaded zip to ~/Documents/chromedriver
- Add the path to conf.ini under variable *CHROME_DRIVER_PATH*


# How to run a script

- For Help: `python insta.py -h`
- To run: `python insta.py -t streetbrand`
