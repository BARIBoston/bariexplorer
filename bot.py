#!/usr/bin/env python3

import collections
import google_streetview.api
import os
import pandas
import time

# Directory to save Google Street View images and metadata files to
IMAGES_DIR = "."
DEFAULT_IMAGE_PATH = "%s/gsv_0.jpg" % IMAGES_DIR

# The CSV file to retrieve data from
INPUT_FILE = "forbot_combined_9_3_shuffled.csv"

# The JSON file where credentials are stored
CREDENTIALS_FILE = "credentials.json"

# File to persist the bot's current place in the input CSV file
STATUS_FILE = "last_idx.txt"

# Miscellaneous constants
VOWELS = "AEIOUaeiou"
DIGITS = "1234567890"

# Time to sleep between new tweets
#SLEEP_TIME = 30 * 60 # 30 minutes
SLEEP_TIME = 60 * 60 # 1 hour

# Dicts to map values as they appear in the CSV file to values as they should
# appear in tweets. The names of the constants roughly follows the format of
# {column name}_MAPPING except where the column name would be unreadable in all
# caps
R_BLDG_STYL_MAPPING = collections.defaultdict(
    lambda: "residential parcel", # default value
    {
        "BL": "Bi-Level",
        "BW": "Bungalow",
        "CL": "Colonial",
        #"CN": "Contemporary",
        "CP": "Cape-style House",
        #"CV": "Conventional",
        "DK": "Triple Decker",
        "DX": "Duplex",
        #"OT": "Other",
        "RE": "Row House",
        "RM": "Row House",
        "RN": "Ranch",
        "RR": "Raised Ranch",
        "SL": "Split Level",
        "TF": "Two-Family Stack",
        "TD": "Tudor",
        "TL": "Tri-Level",
        "SD": "Semidetached",
        "VT": "Victorian"
    }
)
SIMPLIFED_LU_MAPPING = {
    "COMMERCIAL": "commercial parcel",
    "TAX_EXEMPT": "tax exempt parcel",
    "INDUSTRIAL": "industrial parcel",
    "TAX_EXEMPT_BRA": "tax exempt parcel",
    "AGRICULTURAL": "agricultural parcel",
    "MIX_RC": "mixed-use parcel"
}
PERMIT_TYPE_MAPPING = {
    "Short Form Bldg Permit": "short form permit for building renovation",
    "Electrical Permit": "permit for electrical work",
    "Plumbing Permit": "permit for a plumbing work",
    "Gas Permit": "gas permit",
    "Electrical Low Voltage": "permit for electrical work",
    "Certificate of Occupancy": "permit for certificate of occupancy",
    "Long Form/Alteration Permit": "long form permit for alteration",
    "Excavation Permit": "permit for excavation",
    "Electrical Fire Alarms": "permit for fire alarm work",
    "Electrical Temporary Service": "permit for electrical work",
    "Use of Premises": "use of premises permit",
    "Amendment to a Long Form": "amendment to a long form permit",
    "Erect/New Construction": "permit for new construction",
    "Foundation Permit": "foundation permit"
}
ST_NAME_SUF_MAPPING = {
    "AV": "Ave.",
    "RO": "Row",
    "TE": "Ter.",
    "WY": "Way",
    "HW": "Hwy.",
    "PW": "Pkwy.",
    "LA": "Ln.",
    "CI": "Cir.",
    "BL": "Blvd.",
    "PZ": "Plaza",
    "WH": "Wharf",
    "CC": "Circuit",
    "XT": "Ext.",
    "CW": "Crossway"
}
NEIGHBOURHOOD_HASHTAG_MAPPING = {
    "East Boston": "#eastie",
    "Jamaica Plain": "#jp",
    "South Boston": "#southie",
    "South Boston Waterfront": "#seaport"
}

# Special: A "the" is prepended to these neighbourhood values
# e.g. "South End" -> "the South End"
NEIGHBOURHOOD_PREPEND_THE = {
    "South End",
    "North End",
    "West End",
    "South Boston Waterfront",
    "Leather District"
}

# Convert a neighbourhood into a hashtag
def neighbourhood_to_hashtag(neighbourhood_name):
    if (neighbourhood_name in NEIGHBOURHOOD_HASHTAG_MAPPING):
        return NEIGHBOURHOOD_HASHTAG_MAPPING[neighbourhood_name]
    else:
        return "#%s" % neighbourhood_name.lower().replace(" ", "")

# Return the proper article based on whether or not the first character of a
# string is a vowel or not
def article_for(str_):
    if (str_[0] in VOWELS):
        return "an"
    else:
        return "a"

# Returns True if a string contains digits; False otherwise
def contains_digits(str_):
    for digit in DIGITS:
        if (digit in str_):
            return True

# Given an address and lon-lat pair, download the address's Google Street View
# image, falling back to the lon-lat pair if the address has no street number
def pull_picture(address, lon, lat, api_key):
    if (address[0] in DIGITS):
        address = "%s, Boston" % address
    else:
        address = "%d,%d" % (lat, lon)
    results = google_streetview.api\
        .results([{
            "size": "1200x675",
            "location": address,
            "key": api_key
        }])\
        .download_links(IMAGES_DIR)

# Given a string of words, individually capitalize each word
def capitalize_all_words(str_):
    return " ".join([
        word.capitalize()
        for word in str_.split(" ")
    ])

# Given a row of data from the input CSV file, generate a tweet describing its
# attributes, download an image from Google Street View, and return the content
# of that tweet.
def generate_tweet(row, googlemaps_api_key):

    ### Address string: "This parcel on Waymount St." or "72 Day St."

    if (contains_digits(row["ST_NUM"])):
        street_num = row["ST_NUM"].replace(" ", "-")
    else:
        street_num = "This parcel on"

    suffix_raw = row["ST_NAME_SUF"]
    if (suffix_raw in ST_NAME_SUF_MAPPING):
        suffix = ST_NAME_SUF_MAPPING[suffix_raw]
    else:
        if (not pandas.isnull(suffix_raw)):
            suffix = suffix_raw.capitalize() + "."
        else:
            suffix = None

    if (suffix):
        address = " ".join([
            street_num, capitalize_all_words(row["ST_NAME"]), suffix
        ])
    else:
        address = " ".join([
            street_num, capitalize_all_words(row["ST_NAME"])
        ])

    ### Building style: "residential brownstone"
    if (row["SIMPLIFIED_LU"] in SIMPLIFED_LU_MAPPING):
        building_style = SIMPLIFED_LU_MAPPING[row["SIMPLIFIED_LU"]]
    else:
        building_style = R_BLDG_STYL_MAPPING[row["R_BLDG_STYL"]]

    ### Year built
    year = row["YR_BUILT"]
    if (pandas.isnull(year)):
        built_in_year = ""
    else:
        built_in_year = " built in %d" % year

    ### Neighbourhood / section: x section of y
    # We manipulate a list here instead of using string manipulations because
    # several synonyms for a neighbourhood are separated by slashes, and it's
    # easier to do comparisons and modifications on a list of these synonyms
    neighbourhood = row["Name"]
    if (row["NBHDS89_"] == "Cleveland Circle (/Brighton)"):
        sections = ["Cleveland Circle", "Brighton"] # Special case
    else:
        sections = row["NBHDS89_"].split("/")

    # "South End" -> "the South End"
    if (neighbourhood in NEIGHBOURHOOD_PREPEND_THE):
        neighbourhood_fixed = "the %s" % neighbourhood_to_hashtag(neighbourhood)
    else:
        neighbourhood_fixed = neighbourhood_to_hashtag(neighbourhood)

    # "Fenway/West Fens section of Fenway" -> "West Fens section of Fenway"
    try:
        sections.remove(neighbourhood)
    except ValueError:
        pass

    # "in the Charlestown section of Charlestown" -> "in Charlestown"
    if ((len(sections) == 0) or ("Unnamed" in sections)):
        neighbourhood_str = "in %s" % neighbourhood_fixed
    else:
        neighbourhood_str = "in the %s section of %s" % (
            "/".join(sections), neighbourhood_fixed
        )

    ### Assessed value
    assessed_value = "{:,}".format(row["AV_TOTAL"])

    ### Renovations
    year_renovated = row["ISSUED_DATE"]
    if (pandas.isnull(year_renovated)):
        renovated_str = "No building permits were issued for this address since 2006"
    else:
        renovated_str = "A %s was last issued in %d" % (
            PERMIT_TYPE_MAPPING[row["PermitTypeDescr"]], year_renovated
        )

    ### Download picture
    pull_picture(
        "%s, %s" % (address, neighbourhood_fixed),
        row["longitude"], row["latitude"],
        googlemaps_api_key
    )

    return (
        f"{address} is {article_for(building_style)} {building_style}{built_in_year} {neighbourhood_str}."
        f" The current value in the Boston tax assessment database is ${assessed_value}."
        f" {renovated_str}."
    )

if (__name__ == "__main__"):
    import argparse
    import json
    import tweepy

    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--dry-run", dest = "dry_run", action = "store_true", default = False)
    args = parser.parse_args()

    print("loading")

    with open(CREDENTIALS_FILE, "r") as f:
        credentials = json.load(f)

    auth = tweepy.OAuthHandler(
        credentials["twitter"]["consumer_key"],
        credentials["twitter"]["consumer_secret"]
    )
    auth.set_access_token(
        credentials["twitter"]["access_token"],
        credentials["twitter"]["access_token_secret"]
    )
    api = tweepy.API(auth)

    df = pandas.read_csv(INPUT_FILE)
    start_at = 0

    # Load the previous position of the bot
    if (os.path.isfile(STATUS_FILE)):
        with open(STATUS_FILE, "r") as f:
            start_at = int(f.read())

    # Loop over rows
    for (index, row) in df[start_at + 2:].iterrows():
        print("Gathering information for row: %d" % index)
        message = generate_tweet(row, credentials["googlemaps"])

        # Save position
        with open(STATUS_FILE, "w") as f:
            f.write(str(index))

        # Tweet with image
        if (os.path.isfile(DEFAULT_IMAGE_PATH)):
            if (args.dry_run):
                print("Not Tweeting: %s" % message)
            else:
                print("Tweeting: %s" % message)
                status = api.update_with_media(DEFAULT_IMAGE_PATH, message)
            os.remove(DEFAULT_IMAGE_PATH)
            time.sleep(SLEEP_TIME)

        # Tweet without image
        else:
            message = "%s There is no image available for this parcel." % message
            if (args.dry_run):
                print("Not Tweeting: %s" % message)
            else:
                print("Not Tweeting: %s" % message)
                #status = api.update_status(message)


        print("")
