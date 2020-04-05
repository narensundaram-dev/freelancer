## CLIENT REQUIREMENTS:

This is the website we want to scrap: https://www.fasttech.com/products/9701320
as you can see, the structure of the URL is constant, only the product id will change (9701320)

there would be two inputs for the script:
1) product's ID .txt file -
I will manually make a .txt file with only product-id's per line, for example:
9701321
9701322
9701323
9701324
9701325

2) Browse button "Destination Folder" > in this folder data will be scrapped into.
3) USD/GBP multiply value.

script will load the .txt file and run through all product's webpages and the output is this:

1) Open new folder per each product, folder-name will be <product-name> founded on the source-codes of the webpage.
Inside this folder, All JPG's will be saved into.

2) the script will also generate an unique-per-product .txt file contains the description of the product (founded in source-code), file-name: "Description.txt"

3) the script will also generate a ONE General .xlsx (Microsoft) excel file for all products, contains the below columns:
a) Product Name
b) Price
c) Price in GBP (this is simply Price Multiply <Value of USD/GBP Multiply input before)
d) Shipping time (Also found in source-code of product)
