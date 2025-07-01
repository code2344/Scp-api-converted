import os
import json
import re
import time
import argparse
from glob import glob # Added for path matching

# For HTML processing
from bs4 import BeautifulSoup
import html2text

# --- Helper Functions ---

def custom_scp_sort_key(link_key, metadata_dict):
    """
    Custom sorting key for SCP items to ensure SCP-001 comes first,
    followed by its proposals, then other standard SCPs by number.
    This function now needs to handle custom 'metadata' for 001 proposals
    that are found via file system traversal, which won't be in the main index.json.
    """
    # For proposals found via file system traversal, link_key might be the file path
    # We create a pseudo-metadata for them if they aren't in the main dict.
    item_metadata = metadata_dict.get(link_key)
    if not item_metadata and link_key.startswith("scp-001/"):
        # This is a file system discovered 001 proposal
        parts = link_key.split(os.sep)
        proposal_slug = parts[-2] if parts[-1] in ["index.html", "index.txt", "index.md"] else os.path.splitext(parts[-1])[0]
        scp_full_label = f"SCP-001-{proposal_slug.upper().replace('-', '')}" # Guessing a label
        # Create a simple placeholder metadata for sorting
        item_metadata = {'scp': scp_full_label, 'title': proposal_slug.replace('-', ' ').title()}
    elif not item_metadata: # If still no metadata, fallback
        return (99, 999999, link_key) # Put unknown items at the very end

    scp_full_label = item_metadata.get('scp', '')
    scp_number_raw = item_metadata.get('scp_number')

    # Prioritize SCP-001 entries and its proposals
    if scp_full_label and scp_full_label.startswith("SCP-001"):
        if link_key == "scp-001": # Main SCP-001 page
            return (0, 0, "")
        elif link_key.startswith("scp-001-") or link_key.startswith("scp-001/"):
            # Handles both index.json keys like 'scp-001-ex' and
            # file system paths like 'scp-001/proposal-name/index.html'
            if link_key.startswith("scp-001/"): # Extract slug from file path
                parts = link_key.split(os.sep)
                # Handle cases like scp-001/proposal-slug/index.html or scp-001/proposal-slug.html
                if len(parts) >= 2 and (parts[-1].endswith('.html') or parts[-1].endswith('.md') or parts[-1].endswith('.txt')):
                    if parts[-1].startswith('index.'): # e.g., scp-001/proposal-slug/index.html
                        proposal_slug = parts[-2]
                    else: # e.g., scp-001/proposal-slug.html
                        proposal_slug = os.path.splitext(parts[-1])[0]
                else: # Fallback if path structure is unexpected
                    proposal_slug = link_key[len("scp-001/"):]
            else: # From index.json, e.g., 'scp-001-ex'
                proposal_slug = link_key[len("scp-001-"):]

            # Split proposal_slug to handle numbers within slug correctly for sorting
            parts = re.split(r'(\d+)', proposal_slug)
            sortable_parts = []
            for part in parts:
                if part.isdigit():
                    sortable_parts.append(int(part))
                else:
                    sortable_parts.append(part.upper())
            return (0, 1, tuple(sortable_parts)) # All 001 proposals after main 001, sorted by name/numerical parts
        else:
            return (0, 2, link_key) # Fallback for unexpected SCP-001 links

    # For other standard SCPs (e.g., SCP-173, SCP-049) - only pure numbers due to filtering
    if scp_number_raw is not None:
        scp_number_str = str(scp_number_raw)
        match = re.match(r'^(\d+)$', scp_number_str) # Only match pure numbers
        if match:
            num_part = int(match.group(1))
            return (1, num_part, "") # Category 1 for standard items, sorted numerically

    # Fallback for any items that passed filtering but don't match the expected SCP-XXX structure
    return (2, 0, link_key)

def process_text_newlines(text_content):
    """Reduces excessive blank lines to a maximum of two, and strips leading/trailing ones."""
    # Replace 3 or more consecutive newlines with two newlines
    cleaned_text = re.sub(r'\n{3,}', '\n\n', text_content)
    # Strip any leading or trailing blank lines
    cleaned_text = cleaned_text.strip('\n')
    return cleaned_text

def find_scp_001_proposals_html(source_dir):
    """
    Recursively finds HTML files for SCP-001 proposals within the source directory.
    Returns a dictionary mapping a 'pseudo_link_key' (like 'scp-001/proposal-slug/index.html')
    to the raw HTML content and a basic metadata dict.
    """
    scp_001_proposals_data = {}
    scp_001_base_path = os.path.join(source_dir, 'scp-001')

    if not os.path.isdir(scp_001_base_path):
        print(f"Warning: SCP-001 directory not found at {scp_001_base_path}")
        return scp_001_proposals_data

    print(f"Searching for SCP-001 proposals in {scp_001_base_path}...")

    # Look for index.html in subdirectories and direct .html files within scp-001/
    # This specifically looks for index.html within one level of subfolders
    # and any .html files directly under scp-001/
    html_files = glob(os.path.join(scp_001_base_path, '**', 'index.html'), recursive=True)
    html_files.extend(glob(os.path.join(scp_001_base_path, '*.html')))

    # Filter out the main scp-001.html if it's found directly in the scp-001 directory
    # (though typically it's at the level of scp-api-data/docs/data/scp/items/scp-001.html)
    # This check assumes 'source_dir' is 'scp-api-data/docs/data/scp/items'
    main_scp_001_html_path = os.path.join(source_dir, 'scp-001.html')
    if main_scp_001_html_path in html_files:
        html_files.remove(main_scp_001_html_path)

    for html_filepath in html_files:
        try:
            with open(html_filepath, 'r', encoding='utf-8') as f:
                raw_html_content = f.read()

            # Create a unique key for this proposal based on its path
            # e.g., 'scp-001/the-lock/index.html' relative to source_dir
            relative_path = os.path.relpath(html_filepath, source_dir)
            pseudo_link_key = relative_path.replace(os.sep, '/') # Use forward slashes for consistency

            # Extract a basic slug/title for metadata
            # Example: scp-001/proposal-name/index.html -> proposal-name
            # Example: scp-001/proposal-name.html -> proposal-name
            dir_name = os.path.dirname(html_filepath)
            base_filename = os.path.basename(html_filepath)

            if base_filename == 'index.html':
                proposal_slug = os.path.basename(dir_name)
            else:
                proposal_slug = os.path.splitext(base_filename)[0]

            # Try to parse title and object class from the HTML directly if possible
            soup = BeautifulSoup(raw_html_content, 'html.parser')
            title_tag = soup.find(class_='ext-title') or soup.find(id='page-title') or soup.find('title')
            object_class_tag = soup.find(lambda tag: tag.name == 'p' and 'Object Class:' in tag.get_text(strip=True))

            title = title_tag.get_text(strip=True) if title_tag else proposal_slug.replace('-', ' ').title()
            object_class = object_class_tag.get_text(strip=True).replace('Object Class:', '').strip() if object_class_tag else "Unknown"

            scp_full_label = f"SCP-001-{proposal_slug.upper().replace('-', '')}" # Standardize label

            # Create a minimal metadata dictionary for this proposal
            scp_001_proposals_data[pseudo_link_key] = {
                'item_content': {'raw_content': raw_html_content},
                'metadata': {
                    'scp': scp_full_label,
                    'title': title,
                    'object_class': object_class,
                    'link': pseudo_link_key, # Use pseudo_link_key as its own link
                    'scp_number': 001 # Helps with sorting and identification
                }
            }
            print(f"  Found SCP-001 proposal: {scp_full_label} (Source: {relative_path})")

        except Exception as e:
            print(f"Error processing SCP-001 proposal HTML '{html_filepath}': {e}")
            continue
    return scp_001_proposals_data

# --- Main Conversion Function ---

def convert_scp_data(source_dir, output_dir):
    """
    Performs the conversion process from SCP-API data to Markdown and TXT files.
    """
    try:
        # --- Initial Data Loading ---
        metadata_filepath = os.path.join(source_dir, 'index.json')
        content_index_filepath = os.path.join(source_dir, 'content_index.json')

        if not os.path.exists(metadata_filepath) or not os.path.exists(content_index_filepath):
            print(f"Error: Missing index.json or content_index.json in source directory: {source_dir}")
            return False

        print("Loading metadata...")
        with open(metadata_filepath, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        print("Loading content index and data...")
        with open(content_index_filepath, 'r', encoding='utf-8') as f:
            content_index = json.load(f)

        all_content_data = {}
        for series_name, content_filename in content_index.items():
            content_filepath = os.path.join(source_dir, content_filename)
            if os.path.exists(content_filepath):
                try:
                    with open(content_filepath, 'r', encoding='utf-8') as f:
                        series_content = json.load(f)
                    all_content_data.update(series_content)
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode JSON from {content_filepath}. Skipping.")
                except Exception as e:
                    print(f"Warning: An error occurred loading {content_filepath}: {e}")

        # --- Discover and Add SCP-001 Proposals from File System ---
        scp_001_proposals_fs_data = find_scp_001_proposals_html(source_dir)

        # Merge discovered 001 data into main content and metadata structures
        # Use a temporary dict for metadata update to avoid modifying while iterating over keys
        temp_metadata_update = {}
        for pseudo_link_key, data in scp_001_proposals_fs_data.items():
            all_content_data[pseudo_link_key] = data['item_content']
            temp_metadata_update[pseudo_link_key] = data['metadata']
        metadata.update(temp_metadata_update) # Add discovered 001 proposals to main metadata

        # --- Filtering Logic (only standard numbered SCPs and 001 proposals) ---
        filtered_link_keys = []
        pure_numbered_scp_pattern = re.compile(r'^SCP-(\d+)$', re.IGNORECASE)

        for link_key in metadata.keys():
            item_metadata = metadata[link_key]
            scp_full_label = item_metadata.get('scp')

            if not scp_full_label:
                continue

            if scp_full_label.startswith("SCP-001"):
                filtered_link_keys.append(link_key)
            elif pure_numbered_scp_pattern.match(scp_full_label):
                filtered_link_keys.append(link_key)

        sorted_link_keys = sorted(filtered_link_keys, key=lambda k: custom_scp_sort_key(k, metadata))

        total_items_to_process = len(sorted_link_keys)
        print(f"Found {total_items_to_process} SCP items to process (after filtering and 001 discovery).")

        # --- Conversion Loop ---
        processed_count = 0
        conversion_start_time = time.time()

        for link_key in sorted_link_keys:
            item_metadata = metadata[link_key]
            scp_full_label = item_metadata.get('scp')
            scp_number_raw = item_metadata.get('scp_number')

            target_sub_dir = ""
            base_name_for_file = ""

            if scp_full_label and scp_full_label.startswith("SCP-001"):
                # Handle Main SCP-001 and its proposals found via index.json or file system
                if link_key == "scp-001": # The main SCP-001 hub page
                    target_sub_dir = "scp-001"
                    base_name_for_file = "scp-001-hub" # Give it a distinct name
                    # Also try to use a more descriptive title if available for the hub
                    if 'title' in item_metadata and item_metadata['title'] != 'SCP-001':
                         header_title = item_metadata['title']
                    else:
                         header_title = "SCP-001 Hub"

                elif link_key.startswith("scp-001-"): # From index.json, e.g., scp-001-ex
                    proposal_slug = link_key[len("scp-001-"):].lower()
                    target_sub_dir = os.path.join("scp-001", proposal_slug)
                    base_name_for_file = proposal_slug
                    header_title = item_metadata.get('title', scp_full_label) # Use title from metadata if available

                elif link_key.startswith("scp-001/"): # From file system discovery (e.g., scp-001/the-lock/index.html)
                    parts = link_key.split('/')
                    if len(parts) >= 2 and (parts[-1].endswith('.html') or parts[-1].endswith('.md') or parts[-1].endswith('.txt')):
                        if parts[-1].startswith('index.'): # e.g., scp-001/proposal-slug/index.html
                            proposal_slug = parts[-2]
                        else: # e.g., scp-001/proposal-slug.html
                            proposal_slug = os.path.splitext(parts[-1])[0]
                    else:
                        print(f"Warning: Could not determine slug for complex 001 path: {link_key}. Skipping.")
                        processed_count += 1
                        continue

                    target_sub_dir = os.path.join("scp-001", proposal_slug.lower())
                    base_name_for_file = proposal_slug.lower()
                    header_title = item_metadata.get('title', scp_full_label) # Use title from metadata if available

                else:
                    print(f"Warning: Unhandled SCP-001 link_key format: {link_key}. Skipping.")
                    processed_count += 1
                    continue
            else:
                if scp_number_raw is None:
                    print(f"Warning: No scp_number_raw for '{scp_full_label}'. Skipping '{link_key}'.")
                    processed_count += 1
                    continue

                try:
                    num_part_int = int(str(scp_number_raw))
                    padded_num_str = f"{num_part_int:04d}"
                    target_sub_dir = f"scp-{padded_num_str}"
                    base_name_for_file = f"scp-{padded_num_str}"
                    header_title = item_metadata.get('title', scp_full_label)
                except ValueError:
                    print(f"Warning: Malformed SCP number '{scp_number_raw}' for '{scp_full_label}'. Skipping.")
                    processed_count += 1
                    continue

            output_item_dir = os.path.join(output_dir, target_sub_dir)
            os.makedirs(output_item_dir, exist_ok=True)

            md_filepath = os.path.join(output_item_dir, f"{base_name_for_file}.md")
            txt_filepath = os.path.join(output_item_dir, f"{base_name_for_file}.txt")

            item_content_data = all_content_data.get(link_key) # Use a different name to avoid conflict
            raw_html_content = ""
            if item_content_data:
                raw_content = item_content_data.get('raw_content')
                raw_source = item_content_data.get('raw_source') # 'raw_source' is also used in scp-api for content
                if raw_content:
                    raw_html_content = raw_content
                elif raw_source:
                    raw_html_content = raw_source
                else:
                    print(f"Warning: No raw content/source for '{scp_full_label}'. Skipping files for this item.")
                    processed_count += 1
                    continue
            else:
                print(f"Warning: No content found for '{scp_full_label}'. Skipping files for this item.")
                processed_count += 1
                continue

            # --- HTML Cleaning Step ---
            soup = BeautifulSoup(raw_html_content, 'html.parser')

            elements_to_remove_selectors = [
                '.image-credits', '.scp-image-licensing', '.license-box', '.credits-box',
                '.page-tags', '.collapsible-block:has(a.collapsible-block-link[href*="main:license"])',
                '#license-box', '.licensebox', '.anom-bar', # Added .anom-bar
                '.page-options-top', '.page-options-bottom', # Common navigation elements
                'div.footer-wikiwalk-nav' # Specific navigation at the bottom
            ]

            for selector in elements_to_remove_selectors:
                for element in soup.select(selector):
                    element.decompose()

            processed_html_content = str(soup)
            # --- End HTML Cleaning Step ---

            # Prepare header content for both Markdown and Text files
            header_parts = []
            if 'title' in item_metadata:
                header_parts.append(f"# {item_metadata['title']}")
            else:
                header_parts.append(f"# {scp_full_label}")

            header_parts.append(f"Item Number: {scp_full_label}")
            if 'object_class' in item_metadata:
                header_parts.append(f"Object Class: {item_metadata['object_class']}")
            elif 'objectClass' in item_metadata:
                header_parts.append(f"Object Class: {item_metadata['objectClass']}")
            if 'rating' in item_metadata:
                header_parts.append(f"Rating: {item_metadata['rating']}")
            if 'series' in item_metadata:
                header_parts.append(f"Series: {item_metadata['series']}")
            if 'tags' in item_metadata and item_metadata['tags']:
                # Ensure tags is a list before joining
                if isinstance(item_metadata['tags'], list):
                    header_parts.append(f"Tags: {', '.join(item_metadata['tags'])}")
                else:
                    print(f"Warning: Tags for {scp_full_label} is not a list: {item_metadata['tags']}")


            header_str_for_md = "\n".join(header_parts) + "\n\n---\n\n"
            # For TXT, ensure a clean header without markdown formatting
            txt_header_parts = []
            if 'title' in item_metadata:
                txt_header_parts.append(f"Title: {item_metadata['title']}")
            txt_header_parts.append(f"Item Number: {scp_full_label}")
            if 'object_class' in item_metadata:
                txt_header_parts.append(f"Object Class: {item_metadata['object_class']}")
            elif 'objectClass' in item_metadata:
                txt_header_parts.append(f"Object Class: {item_metadata['objectClass']}")
            if 'rating' in item_metadata:
                txt_header_parts.append(f"Rating: {item_metadata['rating']}")
            if 'series' in item_metadata:
                txt_header_parts.append(f"Series: {item_metadata['series']}")
            if 'tags' in item_metadata and item_metadata['tags']:
                 if isinstance(item_metadata['tags'], list):
                    txt_header_parts.append(f"Tags: {', '.join(item_metadata['tags'])}")
            header_str_for_txt = "\n".join(txt_header_parts) + "\n\n"

            # Perform HTML to Markdown and Plain Text Conversion using the PROCESSED HTML
            h = html2text.HTML2Text()
            h.unicode_snob = True; h.body_width = 0; h.ignore_images = False; h.bypass_tables = False; h.single_line_break = True
            md_content = h.handle(processed_html_content)

            html_parser_txt = BeautifulSoup(processed_html_content, 'html.parser')
            txt_content = html_parser_txt.get_text(separator='\n\n')

            final_md_content = header_str_for_md + md_content
            final_txt_content = header_str_for_txt + txt_content

            # --- Newline Reduction Step ---
            final_md_content = process_text_newlines(final_md_content)
            final_txt_content = process_text_newlines(final_txt_content)
            # --- End Newline Reduction Step ---

            # Write converted content to files
            with open(md_filepath, 'w', encoding='utf-8') as f_md:
                f_md.write(final_md_content)

            with open(txt_filepath, 'w', encoding='utf-8') as f_txt:
                f_txt.write(final_txt_content)

            processed_count += 1

            # Print progress and time estimate
            if processed_count % 50 == 0 or processed_count == total_items_to_process:
                elapsed_time = time.time() - conversion_start_time
                if processed_count > 0 and elapsed_time > 0:
                    avg_speed = processed_count / elapsed_time
                    items_remaining = total_items_to_process - processed_count

                    if avg_speed > 0:
                        time_remaining_seconds = items_remaining / avg_speed
                        hours, remainder = divmod(int(time_remaining_seconds), 3600)
                        minutes, seconds = divmod(remainder, 60)

                        time_remaining_str = f"{hours:02d}h {minutes:02d}m {seconds:02d}s"
                    else:
                        time_remaining_str = "Calculating..."
                else:
                    time_remaining_str = "Calculating..."

                print(f"Progress: {processed_count}/{total_items_to_process} items processed. Time Remaining: {time_remaining_str}")

        print(f"Conversion complete! Processed {processed_count} of {total_items_to_process} filtered SCP items.")
        return True

    except Exception as e:
        print(f"An unhandled error occurred during conversion: {e}")
        import traceback
        traceback.print_exc()
        return False

# --- Main execution block for command-line ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert SCP-API data to Markdown and Text files.")
    parser.add_argument('--source', type=str, required=True,
                        help="Path to the source SCP-API data directory (e.g., 'scp-api-data/docs/data/scp/items').")
    parser.add_argument('--output', type=str, required=True,
                        help="Path to the output directory where converted files will be saved.")

    args = parser.parse_args()

    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)

    success = convert_scp_data(args.output, args.source) # Swapped output and source arguments to match script logic
    if not success:
        exit(1) # Exit with a non-zero code on failure for GitHub Actions
