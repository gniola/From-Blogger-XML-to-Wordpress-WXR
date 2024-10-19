#!/usr/bin/env python3

import xml.etree.ElementTree as ET
import os
import sys
import re

# Namespaces for Blogger and WXR
ATOM_NS = '{http://www.w3.org/2005/Atom}'
THR_NS = '{http://purl.org/syndication/thread/1.0}'
WP_NS = 'wp'
CONTENT_NS = 'content'
EXCERPT_NS = 'excerpt'

def create_wxr_root():
    # Create the root of WXR structure
    root = ET.Element("rss", attrib={
        "version": "2.0",
        "xmlns:excerpt": "http://wordpress.org/export/1.2/excerpt/",
        "xmlns:content": "http://purl.org/rss/1.0/modules/content/",
        "xmlns:dc": "http://purl.org/dc/elements/1.1/",
        "xmlns:wp": "http://wordpress.org/export/1.2/"
    })
    channel = ET.SubElement(root, "channel")

    # Set WXR version, which WordPress expects
    ET.SubElement(channel, "wp:wxr_version").text = "1.2"

    ET.SubElement(channel, "title").text = "Blogger to WordPress Export"
    ET.SubElement(channel, "link").text = "https://example.wordpress.com"
    return root, channel

def parse_blogger_xml(blogger_file):
    # Parse the Blogger XML file
    tree = ET.parse(blogger_file)
    root = tree.getroot()
    posts = []
    comments = []

    for entry in root.findall(f'{ATOM_NS}entry'):
        post_id = entry.find(f'{ATOM_NS}id').text
        # Check if entry is a post or a comment based on the presence of <thr:in-reply-to>
        in_reply_to = entry.find(f'{THR_NS}in-reply-to')

        if in_reply_to is None:  # It's a post
            posts.append(entry)
        else:  # It's a comment
            comments.append(entry)

    return posts, comments

def is_valid_label(label):
    # Check if label is a valid tag (not a URL)
    # We assume URLs contain "http" or "www", and we want to exclude them
    return not re.match(r'(https?://|www\.)', label)

def generate_wxr_post(channel, post, post_id):
    # Create WXR post item
    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = post.find(f'{ATOM_NS}title').text or "No Title"
    ET.SubElement(item, "wp:post_id").text = str(post_id)
    ET.SubElement(item, "wp:post_date").text = post.find(f'{ATOM_NS}published').text
    ET.SubElement(item, "content:encoded").text = post.find(f'{ATOM_NS}content').text or ""
    ET.SubElement(item, "wp:status").text = "publish"
    ET.SubElement(item, "wp:post_type").text = "post"

    # Add valid labels (tags) as WordPress tags, filtering out URLs
    for category in post.findall(f'{ATOM_NS}category'):
        label = category.get("term")
        if label and is_valid_label(label):
            # Convert Blogger labels into WordPress post tags
            tag = ET.SubElement(item, "category", domain="post_tag", nicename=label.lower().replace(' ', '-'))
            tag.text = label

    return item

def generate_wxr_comment(item, comment, post_id, comment_id, parent_comment_id=None):
    # Create WXR comment under the correct post item
    wp_comment = ET.SubElement(item, f'{WP_NS}:comment')
    ET.SubElement(wp_comment, f'{WP_NS}:comment_id').text = str(comment_id)
    ET.SubElement(wp_comment, f'{WP_NS}:comment_post_ID').text = str(post_id)  # Link comment to post via post_id
    ET.SubElement(wp_comment, f'{WP_NS}:comment_author').text = comment.find(f'{ATOM_NS}author/{ATOM_NS}name').text
    ET.SubElement(wp_comment, f'{WP_NS}:comment_author_email').text = comment.find(f'{ATOM_NS}author/{ATOM_NS}email').text or "noreply@example.com"
    ET.SubElement(wp_comment, f'{WP_NS}:comment_content').text = comment.find(f'{ATOM_NS}content').text or ""
    ET.SubElement(wp_comment, f'{WP_NS}:comment_date').text = comment.find(f'{ATOM_NS}published').text
    ET.SubElement(wp_comment, f'{WP_NS}:comment_approved').text = "1"

    if parent_comment_id:
        # Set the parent comment ID for nested comments
        ET.SubElement(wp_comment, f'{WP_NS}:comment_parent').text = str(parent_comment_id)
    else:
        # Top-level comment has no parent
        ET.SubElement(wp_comment, f'{WP_NS}:comment_parent').text = "0"

def generate_wxr_author(channel, post):
    # Add author info to the channel (for WXR)
    author_name = post.find(f'{ATOM_NS}author/{ATOM_NS}name').text
    author_email = post.find(f'{ATOM_NS}author/{ATOM_NS}email').text or "noreply@example.com"

    if author_name:
        wp_author = ET.SubElement(channel, f'{WP_NS}:author')
        ET.SubElement(wp_author, f'{WP_NS}:author_id').text = str(abs(hash(author_name)) % (10 ** 8))
        ET.SubElement(wp_author, f'{WP_NS}:author_login').text = author_name.lower().replace(' ', '_')
        ET.SubElement(wp_author, f'{WP_NS}:author_email').text = author_email
        ET.SubElement(wp_author, f'{WP_NS}:author_display_name').text = author_name
        ET.SubElement(wp_author, f'{WP_NS}:author_first_name').text = author_name.split()[0]
        ET.SubElement(wp_author, f'{WP_NS}:author_last_name').text = author_name.split()[-1] if len(author_name.split()) > 1 else ""

def convert_blogger_to_wxr(blogger_file):
    # Define output file path
    output_file = os.path.splitext(blogger_file)[0] + "_to_wordpress.xml"

    # Parse the Blogger XML
    posts, comments = parse_blogger_xml(blogger_file)

    # Create the WXR root structure
    wxr_root, channel = create_wxr_root()

    # Track post and comment IDs
    post_id_map = {}
    comment_id_map = {}  # Track comment IDs
    comment_id_counter = 1

    # Generate unique post and comment IDs
    for i, post in enumerate(posts, start=1):
        post_id = i
        post_id_map[post.find(f'{ATOM_NS}id').text] = post_id

        # Generate post content and author info
        generate_wxr_post(channel, post, post_id)
        generate_wxr_author(channel, post)

    # Generate comments and handle parent-child relationships
    for comment in comments:
        comment_blogger_id = comment.find(f'{ATOM_NS}id').text  # Blogger comment ID

        # Track this comment's WXR ID
        comment_id_map[comment_blogger_id] = comment_id_counter

        original_post_id = comment.find(f'{THR_NS}in-reply-to').attrib['ref']
        post_id = post_id_map.get(original_post_id)

        # Find if the comment is a reply to another comment
        parent_comment_ref = comment.find(f'{THR_NS}in-reply-to').attrib.get('ref', None)
        parent_comment_id = comment_id_map.get(parent_comment_ref) if parent_comment_ref else None

        # Find the post item corresponding to the post_id
        post_item = [i for i in channel.findall("item") if i.find(f'{WP_NS}:post_id').text == str(post_id)]
        if post_item:
            generate_wxr_comment(post_item[0], comment, post_id, comment_id_counter, parent_comment_id)
            comment_id_counter += 1

    # Write the output WXR file
    tree = ET.ElementTree(wxr_root)
    tree.write(output_file, encoding="utf-8", xml_declaration=True)
    print(f"Conversion completed. WXR file saved at: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python convert_blogger_to_wxr.py <blogger_xml_file>")
        sys.exit(1)

    blogger_file = sys.argv[1]

    if not os.path.isfile(blogger_file):
        print(f"File {blogger_file} not found.")
        sys.exit(1)

    convert_blogger_to_wxr(blogger_file)
