# About the @BARIexplorer Twitter bot
*by Will Pfeffer, Riley Tucker, Edgar Castro, and Saina Sheini*

A few times each year, the [Boston Area Research Initiative](https://www.northeastern.edu/csshresearch/bostonarearesearchinitiative) releases updated datasets to the public. At each data release, members of our research team write blog posts detailing mini research projects, as a way to demonstrate the kind of questions these data can answer. Most of these projects are fairly small, discrete research questions–although some do relate to ongoing BARI research projects.

For our most recent data release, we decided to do something a little different. Inspired by Twitter bots like [@everycensustract](https://twitter.com/everytract) and [@everylotboston](https://twitter.com/everylotboston), we decided to [build our own Twitter bot](https://twitter.com/BARIexplorer) in Python, which would draw on some of the datasets we rely on in our more formal research: [building permits](https://doi.org/10.7910/DVN/N4BL71) and [property assessments](https://doi.org/10.7910/DVN/YVKZIG). The property assessment data contains not just the assessed value of each parcel, but also details about the year of construction, type of use (residential, commercial, etc.), and in many cases even the architectural style of each residential structure. By bringing in building permit data, we’re able to look at a small sliver of a building’s history. Finally, we add in a visual element by sending the parcel’s location to the Google Maps Street View API, which returns an image that we include in each post.

![@BARIexplorer screenshot](https://www.northeastern.edu/csshresearch/bostonarearesearchinitiative/wp-content/uploads/sites/2/2019/09/explorer.png)

Using the [Geographical Infrastructure](https://www.northeastern.edu/csshresearch/bostonarearesearchinitiative/2018/11/12/data-stories-2018-geographical-infrastructure-for-boston/) we have built, we’re able to geolocate each parcel to pull in even more information. We use this to describe the location of each parcel within a neighborhood, using both the [City of Boston’s defined administrative boundaries](https://doi.org/10.7910/DVN/JZV6ON) and the sub-neighborhoods defined in the [Boston Neighborhood Survey](https://doi.org/10.7910/DVN/SE2CIX).

After deciding on the format of each tweet, and determining which variables we wanted to include, our first task was to assemble the dataset we’d use to build each tweet. In order to retrieve our desired information, we merged the “Property Assessment” and “Building Permit” data sets. These data sets include information about the property value, address and permit types along with BARI’s Geographical Infrastructure variables. The resulting dataset represents 23 variables describing each parcel in Boston.

To include the Google Street View imagery, we create a query containing information on each parcel from our database using the Google Maps Street View API. To retrieve the most spatially precise image, we construct a query based on the address of each parcel that also specifies the dimensions of each image and our API key, an individualized token provided by Google that allows us to retrieve and download the images:

However, in some cases it is not possible to search for a parcel based on address; a small proportion of parcels have incomplete or incorrectly entered addresses and many are vacant lots that simply have not been assigned an address by the city. In these cases, we instead construct a query based on the longitudinal and latitudinal coordinates of the centroid (or geographic center) of each parcel.

```
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
  ```
  
The construction of the sentences as they appear in each tweet involves a series of steps involving string comparisons and manipulations. Sometimes, the only additional processing that needs to be done is some capitalization and concatenation of strings; in other cases, as in the street suffixes and permit types, the script pulls from a collection of predefined text that maps each value as it appears in the data file to a string that would better fit in the context of the tweet. Most complicated processing such as geospatial joins of parcel geometries to neighborhood geometries and aggregations of duplicate data is done beforehand in order to reduce load on the server where the bot is deployed.

[See the full code on Github](https://github.com/BARIBoston/bariexplorer/blob/master/bot.py)

After each loop, the index of the most recently processed row is stored on disk in a text file. On subsequent launches, the bot loads this index from the text file and skips to that row in the data file before resuming normal operation.

We plan to continue updating and adding to the bot as we release new data and generate new ideas. We welcome feedback and collaboration: get in touch at BARI@northeastern.edu!
