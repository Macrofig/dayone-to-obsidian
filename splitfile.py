import datetime
import dateutil.parser
import json
import pytz    # pip install pytz
import re
import os
import sys
import shutil
import time

# Set this as the location where your Journal.json file is located
root = r"../photo-journal" 
icons = False   # Set to true if you are using the Icons Plugin in Obsidian
tagPrefix = "#journal/"  # This will append journal/ as part of the tag name for sub-tags ie. instead of #entry, it is #journal/entry. To exclude set to "". If you change journal to something else, make sure you keep the trailing /


journalFolder = os.path.join(root, "journal") #name of folder where journal entries will end up
fn = os.path.join( root, "Journal.json" )

# Clean out existing journal folder, otherwise each run creates new files
if os.path.isdir(journalFolder):
    print ("Deleting existing folder: %s" % journalFolder)
    shutil.rmtree(journalFolder)

time.sleep(2)  # Give time for folder deletion to complete. Only a problem if you have the folder open when trying to run the script
if not os.path.isdir(journalFolder):
    print( "Creating journal folder: %s" % journalFolder)
    os.mkdir(journalFolder)

if icons:
    print ("Icons are on")
    dateIcon = "`fas:CalendarAlt` "
else:
    print ("Icons are off")
    dateIcon = ""  #make 2nd level heading


print( "Begin processing entries")
count = 0
with open(fn, encoding='utf-8') as json_file:
    data = json.load(json_file)
    for entry in data['entries']:
        newEntry = []

        createDate = dateutil.parser.isoparse(entry['creationDate'])
        localDate = createDate.astimezone(pytz.timezone(entry['timeZone'])) # It's natural to use our local date/time as reference point, not UTC
 
        # Add location
        location = ''
        for locale in ['placeName', 'localityName', 'administrativeArea', 'country']:
            try:
                location = "%s, %s" % (location, entry['location'][locale] )
            except KeyError:
                pass
        location = location[2:]

        dateCreated = str(createDate)
        coordinates = ''

        frontmatter = ['- created: '+ dateCreated]
        if 'location' in entry:
            coordinates = str(entry['location']['latitude']) + ',' + str(entry['location']['longitude'])
            frontmatter.append('- location: [' + coordinates + ']')

        # newEntry.append(frontmatter)
        # Add body text if it exists (can have the odd blank entry), after some tidying up
        try:
            newText = entry['text'].replace("\\", "")
            newText = newText.replace( "\u2028", "\n")
            newText = newText.replace( "\u1C6A", "\n\n")
            # Extract title
            # "^#\s[^#\n]+([\W\w]*?)"gm finds instances of an h1
            h1s = re.findall(r"^#\s[\w\s]+\n", newText, re.MULTILINE)
            if h1s.count:
                title = h1s[0].replace( "\n", "" )
                title = title.replace( "# ", "" )

                print('Detected title, %s' % title)
                frontmatter.append('- title: %s' % title)
            newText = '''---
''' + '\n'.join(frontmatter) + '''
---

''' + newText

            if 'photos' in entry:
                # Correct photo links. First we need to rename them. The filename is the md5 code, not the identifier
                # subsequently used in the text. Then we can amend the text to match. Will only to rename on first run
                # through as then, they are all renamed.

                for p in entry['photos']:
                    pfn = os.path.join( root, 'photos', '%s.%s' % (p['md5'], p['type']) )
                    print ( 'Checking for %s' % pfn)
                    if os.path.isfile( pfn ):
                        newfn = os.path.join( root, 'photos', '%s.%s' % (p['identifier'], p['type']) )
                        print ( 'Renaming %s to %s' % (pfn, newfn ))
                        os.rename( pfn, newfn )

                # Now to replace the text to point to the file in obsidian
                newText = re.sub(r"(\!\[\]\(dayone-moment:\/\/)([A-F0-9]+)(\))", r'![[\2.%s]]' % p['type'], newText)

            newEntry.append( newText )
        except KeyError:
            pass

        ## Start Metadata section
        newEntry.append( '\n\n---\n' )

        if not location == '':
            newEntry.append( '- Location: [[%s]]\n' % location) # Remove leading ", "

            if coordinates == []:
                locationString =  location 
            else:
                locationString = '[' + location + '](geo:' + coordinates + ')'
            newEntry.append( locationString ) 

        tags = []
        if 'tags' in entry:
            tags = []
            for t in entry['tags']:
                tags.append( "%s%s" % (tagPrefix, t.replace(' ', '-').replace('---', '-') ) )
            if entry['starred']:
                tags.append( "%sstarred" % (tagPrefix) )
        if len(tags) > 0:
            newEntry.append( "- Tags: %s\n" % " ".join( tags ))



        # Save entries organised by year, year-month, year-month-day.md
        yearDir = os.path.join( journalFolder, str(createDate.year) )
        monthDir = os.path.join( yearDir, createDate.strftime( '%Y-%m'))

        if not os.path.isdir(yearDir):
            os.mkdir(yearDir)
        
        if not os.path.isdir(monthDir):
            os.mkdir(monthDir)
        
        # Target filename to save to. Will be modified if already exists
        if not title:
            title = localDate.strftime( '%Y-%m-%d')
        fnNew = os.path.join( monthDir, "%s.md" % title)
        
        # Here is where we handle multiple entries on the same day. Each goes to it's own file
        if os.path.isfile( fnNew):
            # File exists, need to find the next in sequence and append alpha character marker
            index = 97 #ASCII a
            fnNew = os.path.join( monthDir, "%s%s.md" % (title, chr(index)))
            while os.path.isfile(fnNew):
                index += 1
                fnNew = os.path.join( monthDir, "%s%s.md" % (title, chr(index)))


        with open(fnNew, 'w', encoding='utf-8') as f:
         for line in newEntry:
            f.write(line)

        count += 1

print ("Complete: %d entries processed." % count)

