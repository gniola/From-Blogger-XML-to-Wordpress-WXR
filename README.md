# From-Blogger-XML-to-Wordpress-WXR
This is a very simple script programmed in python that manages to turn a Blogger XML file in a WXR XML file, good for importing in Wordpress. Though Wordpress already has this function embedded, sometimes XML files larger than 20MB or 40MB aren't easily uploaded. This script parses the XML file exported from blogger, mantanis usernames, nicknames, date and preserves images links.

Most important it correctly handles comments and nested comments.

USAGE: source file would be the first parameter and the new WXR file will be saved in the same folder as the source one.

EXAMPLE: python3 XMLtoWXR.py '/home/Downloads/blogger.xml' 
will generate a blogger_to_wordpress.xml file in the Downloads folder
