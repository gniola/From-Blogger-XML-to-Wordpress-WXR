#!/usr/bin/env python3

import xml.etree.ElementTree as ET
import os
import re
import sys
from tkinter import Tk, Label, Button, Entry, filedialog, messagebox, StringVar
from tkinter.ttk import Progressbar
import threading

ATOM_NS = '{http://www.w3.org/2005/Atom}'
THR_NS = '{http://purl.org/syndication/thread/1.0}'
WP_NS = 'wp'
CONTENT_NS = 'content'
EXCERPT_NS = 'excerpt'

# Function to create WXR root (as in the original script)
def create_wxr_root():
    root = ET.Element("rss", attrib={
        "version": "2.0",
        "xmlns:excerpt": "http://wordpress.org/export/1.2/excerpt/",
        "xmlns:content": "http://purl.org/rss/1.0/modules/content/",
        "xmlns:dc": "http://purl.org/dc/elements/1.1/",
        "xmlns:wp": "http://wordpress.org/export/1.2/"
    })
    channel = ET.SubElement(root, "channel")
    ET.SubElement(channel, "wp:wxr_version").text = "1.2"
    ET.SubElement(channel, "title").text = "Blogger to WordPress Export"
    ET.SubElement(channel, "link").text = "https://example.wordpress.com"
    return root, channel

def is_valid_label(label):
    return not re.match(r'(https?://|www\.)', label)

# GUI Application class
class BloggerToWXRConverter:
    def __init__(self, master):
        self.master = master
        master.title("Blogger to WXR Converter")

        self.source_file_path = StringVar()
        self.destination_file_path = StringVar()

        # Label and Entry for source file
        self.label_source = Label(master, text="Select Source Blogger XML")
        self.label_source.grid(row=0, column=0)
        self.entry_source = Entry(master, textvariable=self.source_file_path, width=40)
        self.entry_source.grid(row=0, column=1)
        self.button_source = Button(master, text="Browse", command=self.browse_source_file)
        self.button_source.grid(row=0, column=2)

        # Label and Entry for destination file
        self.label_destination = Label(master, text="Select Destination WXR File")
        self.label_destination.grid(row=1, column=0)
        self.entry_destination = Entry(master, textvariable=self.destination_file_path, width=40)
        self.entry_destination.grid(row=1, column=1)
        self.button_destination = Button(master, text="Browse", command=self.browse_destination_file)
        self.button_destination.grid(row=1, column=2)

        # Progress Bar
        self.progress = Progressbar(master, orient="horizontal", length=300, mode='determinate')
        self.progress.grid(row=2, columnspan=3)

        # Start and Cancel buttons
        self.button_start = Button(master, text="Start", command=self.start_conversion)
        self.button_start.grid(row=3, column=1)
        self.button_cancel = Button(master, text="Cancel", command=master.quit)
        self.button_cancel.grid(row=3, column=2)

    def browse_source_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("XML files", "*.xml")])
        self.source_file_path.set(file_path)

    def browse_destination_file(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".xml", filetypes=[("XML files", "*.xml")])
        self.destination_file_path.set(file_path)

    def start_conversion(self):
        # Validate file selection
        source = self.source_file_path.get()
        destination = self.destination_file_path.get()
        if not source or not destination:
            messagebox.showerror("Error", "Please select both source and destination files.")
            return

        # Start the conversion in a separate thread to avoid freezing the GUI
        threading.Thread(target=self.convert_blogger_to_wxr, args=(source, destination)).start()

    def convert_blogger_to_wxr(self, blogger_file, output_file):
        try:
            self.progress['value'] = 0
            posts, comments = self.parse_blogger_xml(blogger_file)
            wxr_root, channel = create_wxr_root()

            post_id_map = {}
            comment_id_map = {}
            comment_id_counter = 1

            # Process posts
            for i, post in enumerate(posts, start=1):
                post_id_map[post.find(f'{ATOM_NS}id').text] = i
                self.generate_wxr_post(channel, post, i)
                self.generate_wxr_author(channel, post)
                self.progress['value'] += (50 / len(posts))  # Update progress by 50% through posts
                self.master.update_idletasks()

            # Process comments
            for comment in comments:
                comment_blogger_id = comment.find(f'{ATOM_NS}id').text
                comment_id_map[comment_blogger_id] = comment_id_counter
                original_post_id = comment.find(f'{THR_NS}in-reply-to').attrib['ref']
                post_id = post_id_map.get(original_post_id)
                post_item = [i for i in channel.findall("item") if i.find(f'{WP_NS}:post_id').text == str(post_id)]
                if post_item:
                    self.generate_wxr_comment(post_item[0], comment, post_id, comment_id_counter)
                    comment_id_counter += 1
                self.progress['value'] += (50 / len(comments))  # Update progress by 50% through comments
                self.master.update_idletasks()

            # Write the output WXR file
            tree = ET.ElementTree(wxr_root)
            tree.write(output_file, encoding="utf-8", xml_declaration=True)
            messagebox.showinfo("Success", f"Conversion completed. WXR file saved at: {output_file}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def parse_blogger_xml(self, blogger_file):
        tree = ET.parse(blogger_file)
        root = tree.getroot()
        posts = []
        comments = []
        for entry in root.findall(f'{ATOM_NS}entry'):
            in_reply_to = entry.find(f'{THR_NS}in-reply-to')
            if in_reply_to is None:
                posts.append(entry)
            else:
                comments.append(entry)
        return posts, comments

    def generate_wxr_post(self, channel, post, post_id):
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = post.find(f'{ATOM_NS}title').text or "No Title"
        ET.SubElement(item, "wp:post_id").text = str(post_id)
        ET.SubElement(item, "wp:post_date").text = post.find(f'{ATOM_NS}published').text
        ET.SubElement(item, "content:encoded").text = post.find(f'{ATOM_NS}content').text or ""
        ET.SubElement(item, "wp:status").text = "publish"
        ET.SubElement(item, "wp:post_type").text = "post"
        for category in post.findall(f'{ATOM_NS}category'):
            label = category.get("term")
            if label and is_valid_label(label):
                tag = ET.SubElement(item, "category", domain="post_tag", nicename=label.lower().replace(' ', '-'))
                tag.text = label

    def generate_wxr_author(self, channel, post):
        author_name = post.find(f'{ATOM_NS}author/{ATOM_NS}name').text
        author_email = post.find(f'{ATOM_NS}author/{ATOM_NS}email').text or "noreply@example.com"
        if author_name:
            wp_author = ET.SubElement(channel, f'{WP_NS}:author')
            ET.SubElement(wp_author, f'{WP_NS}:author_id').text = str(abs(hash(author_name)) % (10 ** 8))
            ET.SubElement(wp_author, f'{WP_NS}:author_login').text = author_name.lower().replace(' ', '_')
            ET.SubElement(wp_author, f'{WP_NS}:author_email').text = author_email
            ET.SubElement(wp_author, f'{WP_NS}:author_display_name').text = author_name

    def generate_wxr_comment(self, item, comment, post_id, comment_id, parent_comment_id=None):
        wp_comment = ET.SubElement(item, f'{WP_NS}:comment')
        ET.SubElement(wp_comment, f'{WP_NS}:comment_id').text = str(comment_id)
        ET.SubElement(wp_comment, f'{WP_NS}:comment_post_ID').text = str(post_id)
        ET.SubElement(wp_comment, f'{WP_NS}:comment_author').text = comment.find(f'{ATOM_NS}author/{ATOM_NS}name').text
        ET.SubElement(wp_comment, f'{WP_NS}:comment_content').text = comment.find(f'{ATOM_NS}content').text or ""
        ET.SubElement(wp_comment, f'{WP_NS}:comment_date').text = comment.find(f'{ATOM_NS}published').text
        ET.SubElement(wp_comment, f'{WP_NS}:comment_approved').text = "1"
        if parent_comment_id:
            ET.SubElement(wp_comment, f'{WP_NS}:comment_parent').text = str(parent_comment_id)
        else:
            ET.SubElement(wp_comment, f'{WP_NS}:comment_parent').text = "0"

if __name__ == "__main__":
    root = Tk()
    converter = BloggerToWXRConverter(root)
    root.mainloop()
