import csv
import os
import tkinter as tk
import threading
import time
from sys import exit

from evaluate import Site, parse_site_list, desktop_site_list, mobile_site_list, sitelist_filename
from evaluate import desktop_browser, mobile_browser, cleanup_browser

browser = None
state = {}
buttons = []
entry_vars = {}
default_buttons = []
def reset_state():
    global state
    state = {
        # some state is commented as it contained in the entry StringVars
        #'colour': '#000000',
        #'background colour': '#000000',
        'size': 'average',
        'location': 'top right',
        'type': 'button',
        'sticky': True,
        'visible': 'Yes',
        #'label': '',
        #'clicks to exit': '',
        #'landing': [],
    }
    # Reset all highlighting
    for btn in buttons:
        btn.configure(bg='#ffffff')
    # Highlight default options
    for btn in default_buttons:
        btn.configure(bg='#00c000')
    # Clear entered text
    for entry in entry_vars:
        entry_vars[entry].set('')
    # Add some default values
    entry_vars['background colour'].set('#FFFFFF')
    entry_vars['clicks to exit'].set('1')

# Event handlers for selection buttons
loc_btns = []
def click_loc_btn(location):
    state['location'] = location
    for btn in loc_btns:
        if btn.cget('text') == location:
            btn.configure(bg='#00c000')
        else:
            btn.configure(bg='#ffffff')

size_btns = []
def click_size_btn(size):
    state['size'] = size
    for btn in size_btns:
        if btn.cget('text') == size:
            btn.configure(bg='#00c000')
        else:
            btn.configure(bg='#ffffff')

type_btns = []
def click_type_btn(btn_type):
    state['type'] = btn_type
    for btn in type_btns:
        if btn.cget('text') == btn_type:
            btn.configure(bg='#00c000')
        else:
            btn.configure(bg='#ffffff')

sticky_btns = []
def click_sticky_btn(sticky):
    state['sticky'] = sticky == 'Yes'
    for btn in sticky_btns:
        if btn.cget('text') == sticky:
            btn.configure(bg='#00c000')
        else:
            btn.configure(bg='#ffffff')

visible_btns = []
def click_visible_btn(visible):
    state['visible'] = visible
    for btn in visible_btns:
        if btn.cget('text') == visible:
            btn.configure(bg='#00c000')
        else:
            btn.configure(bg='#ffffff')

def click_url_btn():
    global browser
    browser.get(entry_vars['url'].get())

def click_text_btn():
    click_type_btn("text")
    click_size_btn("text")

landing_entry = None
def save_landing_sites():
    global browser
    state['landing'] = []
    for handle in browser.window_handles:
        browser.switch_to.window(handle)
        state['landing'].append(browser.current_url)
    combined_list = ';'.join(state['landing'])
    entry_vars['landing'].set(combined_list)

mechanism_info_filename = 'site_info.csv'
def load_completed_annotations():
    if not os.path.exists(mechanism_info_filename):
        return "", {}
    urls = []
    with open(mechanism_info_filename, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            urls.append((row['URL'], row['Platform']))
    return urls

def save_completed_annotation():
    # Build record from variables
    record = [
        entry_vars['url'].get(), entry_vars['platform'].get(),
        # Properties: Button colour, site Background Colour, Button Size
        entry_vars['colour'].get(), entry_vars['background colour'].get(), state['size'],
        # Location on screen, type of button (button/banner/image)
        state['location'], state['type'],
        # booleans: stays on scroll, visible on first load,
        state['sticky'], state['visible'],
        # text label (if any), num. clicks required, landing page(s)
        entry_vars['label'].get(), entry_vars['clicks to exit'].get(), entry_vars['landing'].get()
    ]
    print(record)
    # Convert to csv and write to file
    with open(mechanism_info_filename, "a", newline='') as f:
        writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(record)

def make_eval_window():
    global landing_entry
    window = tk.Tk()
    window.title('Site Button Info')
    window.geometry('250x650+1400+50')
    info_frame = tk.Frame(window)
    entry_vars['url'] = tk.StringVar(value="URL")
    site_url_lbl = tk.Button(info_frame, textvariable=entry_vars['url'], command=click_url_btn)
    site_url_lbl.grid()
    entry_vars['platform'] = tk.StringVar(value="[Desktop]")
    platform_lbl = tk.Label(info_frame, textvariable=entry_vars['platform'])
    platform_lbl.grid(row=1)
    info_frame.grid(sticky='nesw')
    # Generate variables for text entries
    entry_vars['colour'] = tk.StringVar()
    entry_vars['background colour'] = tk.StringVar()
    entry_vars['clicks to exit'] = tk.StringVar()
    entry_vars['label'] = tk.StringVar()
    entry_vars['landing'] = tk.StringVar()
    # colour, background colour
    btn_properties_frame = tk.Frame(window)
    tk.Label(btn_properties_frame, text="colour:").grid(row=0)
    tk.Entry(btn_properties_frame, textvariable=entry_vars['colour']).grid(row=0, column=1)
    tk.Label(btn_properties_frame, text="background:").grid(row=1)
    tk.Entry(btn_properties_frame, textvariable=entry_vars['background colour']).grid(row=1, column=1)
    tk.Label(btn_properties_frame, text="size:").grid(row=2)
    sizes = ['text', 'small', 'average',
             'wide', 'long', 'large']
    for r in range(2):
        for c in range(3):
            button = tk.Button(btn_properties_frame, text=sizes[3 * r + c], bg='#ffffff',
                               command=(lambda size=sizes[3*r+c]: click_size_btn(size)))
            if r==0 and c==0:
                button.configure(command=click_text_btn)
            if r==0 and c==2:
                button.configure(bg='#00c000')
                default_buttons.append(button)
            button.grid(row=r + 3, column=c, sticky='nesw')
            size_btns.append(button)
            buttons.append(button)
    btn_properties_frame.grid(row=1, sticky='nesw')
    # Location in window (possibly multiple)
    location_frame = tk.Frame(window)
    tk.Label(location_frame, text="Button location:").grid(sticky='nesw', columnspan=3)
    locations = ['top left', 'top', 'top right',
                 'left', 'content', 'right',
                 'bottom left', 'bottom', 'bottom right',
                 'dropdown', 'side menu', 'other']
    for r in range(4):
        for c in range(3):
            button = tk.Button(location_frame, text=locations[3 * r + c], bg='#ffffff',
                               command=(lambda loc=locations[3*r+c]: click_loc_btn(loc)))
            if r==0 and c==2:
                button.configure(bg='#00c000')
                default_buttons.append(button)
            button.grid(row=r + 1, column=c, sticky='nesw')
            loc_btns.append(button)
            buttons.append(button)
    location_frame.grid(row=2, sticky='nesw')
    # type: # button/banner/image/menu item
    type_frame = tk.Frame(window)
    tk.Label(type_frame, text="Type of button:").grid(sticky='nesw', columnspan=3)
    types = ['button', 'banner', 'image', 'menu item', 'text']
    for i, t in enumerate(types):
        button = tk.Button(type_frame, text=t, bg='#ffffff',
                           command=(lambda t=t: click_type_btn(t)))
        if i == 0:
            button.configure(bg='#00c000')
            default_buttons.append(button)
        if i == 4:
            button.configure(command=click_text_btn)
        button.grid(row=1, column=i, sticky='nesw')
        type_btns.append(button)
        buttons.append(button)
    type_frame.grid(row=3, sticky='nesw')
    # Booleans: Is sticky / scrolls with page, visible on first load
    bools_frame = tk.Frame(window)
    tk.Label(bools_frame, text="Is the button sticky?").grid(row=0, sticky='nesw', columnspan=2)
    is_sticky = tk.Button(bools_frame, text='Yes', bg='#00c0ff', command=(lambda: click_sticky_btn('Yes'))); is_sticky.grid(row=1, sticky='nesw')
    not_sticky = tk.Button(bools_frame, text='No', bg='#ffffff', command=(lambda: click_sticky_btn('No'))); not_sticky.grid(row=1, column=1, sticky='nesw')
    buttons.append(is_sticky); buttons.append(not_sticky); default_buttons.append(is_sticky)
    sticky_btns.append(is_sticky); sticky_btns.append(not_sticky)
    tk.Label(bools_frame, text="Is the button visible on first load?").grid(row=2, sticky='nesw', columnspan=2)
    is_visible = tk.Button(bools_frame, text='Yes', bg='#00c000', command=(lambda: click_visible_btn('Yes'))); is_visible.grid(row=3, sticky='nesw')
    cookie_visible = tk.Button(bools_frame, text='Cookie Notice', bg='#ffffff', command=(lambda: click_visible_btn('Cookie Notice'))); cookie_visible.grid(row=3, column=1, sticky='nesw')
    not_visible = tk.Button(bools_frame, text='No', bg='#ffffff', command=(lambda: click_visible_btn('No'))); not_visible.grid(row=3, column=2, sticky='nesw')
    buttons.append(is_visible); buttons.append(cookie_visible); buttons.append(not_visible); default_buttons.append(is_visible)
    visible_btns.append(is_visible); visible_btns.append(cookie_visible); visible_btns.append(not_visible)
    bools_frame.grid(row=4, sticky='nesw')
    # clicks
    num_clicks_frame = tk.Frame(window)
    tk.Label(num_clicks_frame, text="Number of clicks for button").grid(sticky='nesw')
    num_clicks_entry = tk.Entry(num_clicks_frame, textvariable=entry_vars['clicks to exit']); num_clicks_entry.grid()
    num_clicks_frame.grid(row=5, sticky='nesw')
    # Label (text indicating it is an exit button, if present
    label_frame = tk.Frame(window)
    tk.Label(label_frame, text="Label of button, if any").grid(sticky='nesw')
    label_entry = tk.Entry(label_frame, textvariable=entry_vars['label']); label_entry.grid()
    label_frame.grid(row=6, sticky='nesw')
    # landing site
    landing_frame = tk.Frame(window)
    tk.Label(landing_frame, text="Landing URL(s):").grid()
    landing_entry = tk.Entry(landing_frame, textvariable=entry_vars['landing']); landing_entry.grid(row=1)
    tk.Button(landing_frame, text='Save current URL(s) as landing site(s)', bg='#ffffff',
              command=save_landing_sites).grid(row=2)
    landing_frame.grid(row=7, sticky='nesw')

    # save page results (conditional on things present)
    save_btn = tk.Button(window, text="Save", command=save_and_next)
    save_btn.grid(row=8, pady=25, columnspan=3, sticky="nesw")

    return window

def set_site(site, platform):
    global browser
    entry_vars['url'].set(site.url)
    entry_vars['platform'].set(platform)
    browser.get(site.url)

def save_and_next():
    global browser
    # Save this annotation
    save_completed_annotation()

    # Remove the completed site
    current_platform = entry_vars['platform'].get()
    if current_platform == 'Desktop':
        del desktop_site_list[0]
    elif current_platform == 'Mobile':
        del mobile_site_list[0]
    else:
        raise Exception('Invalid current platform: '+current_platform)

    # Reset variables
    reset_state()
    # Cleanup extra tabs etc
    cleanup_browser()

    # Go to next site
    if len(desktop_site_list) > 0:
        set_site(desktop_site_list[0], 'Desktop')
    elif len(mobile_site_list) > 0:
        if current_platform == 'Desktop':
            entry_vars['platform'] = 'Mobile'
            browser.quit()
            browser = mobile_browser()
        set_site(mobile_site_list[0], 'Mobile')
    else:
        if browser:
            browser.quit()
        print("You're done with annotations!")
        exit(0)


if __name__ == '__main__':
    parse_site_list()
    # Make window
    root = make_eval_window()

    # Read list of sites to annotate
    annotated = load_completed_annotations()
    for (url, platform) in annotated:
        cs = Site(url, mobile_site=(platform=='Mobile'))
        if platform == 'Desktop' and cs in desktop_site_list:
            desktop_site_list.remove(cs)
        elif platform == 'Mobile' and cs in mobile_site_list:
            mobile_site_list.remove(cs)
        else:
            raise Exception("Unknown platform: " + platform)
    print(f"You have {len(desktop_site_list)} desktop sites and {len(mobile_site_list)} mobile sites remaining.")

    # Reset state before starting
    reset_state()

    # Initialise browser
    if len(desktop_site_list) > 0:
        browser = desktop_browser()
        set_site(desktop_site_list[0], 'Desktop')
    elif len(mobile_site_list) > 0:
        browser = mobile_browser()
        set_site(mobile_site_list[0], 'Mobile')
    else:
        print("You're done with annotations!")
        exit(0)

    # Go into UI loop
    root.mainloop()

    # Cleanup on exit
    browser.quit()
