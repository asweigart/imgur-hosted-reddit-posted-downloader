import re, praw, requests, os, glob, sys

MIN_SCORE = 100 # the default minimum score before it is downloaded

if len(sys.argv) < 2:
	# no command line options sent:
	print('Usage:')
	print('  python %s subreddit [minimum score]' % (sys.argv[0]))
	sys.exit()
elif len(sys.argv) >= 2:
	# the subreddit was specified:
	targetSubreddit = sys.argv[1]
	if len(sys.argv) >= 3:
		# the desired minimum score was also specified:
		MIN_SCORE = sys.argv[2]


imagePattern = re.compile(r'<a href="(http://i.imgur.com/(.*?))(\?.*?)?" target="_blank">View full resolution</a>')
imgTagPattern = re.compile(r'<img src="(http://i.imgur.com/(.*?))(\?.*?)?"')
imgurUrlPattern = re.compile(r'(http://i.imgur.com/(.*))(\?.*)?')


# Connect to reddit and download the subreddit front page
r = praw.Reddit(user_agent='CHANGE THIS TO A UNIQUE VALUE') # Note: Be sure to change the user-agent to something unique.
posts = r.get_subreddit(targetSubreddit).get_hot(limit=25)
# Or use one of these functions:
#                                       .get_top_from_year(limit=25)
#                                       .get_top_from_month(limit=25)
#                                       .get_top_from_week(limit=25)
#                                       .get_top_from_day(limit=25)
#                                       .get_top_from_hour(limit=25)
#                                       .get_top_from_all(limit=25)

# Process all the posts from the front page
for post in posts:
	# Check for all the cases where we will skip a post:
	if "imgur.com/" not in post.url:
		continue # skip non-imgur posts
	if post.score < MIN_SCORE:
		continue # skip posts that haven't even reached 100 (thought this should be rare if we're collecting the "hot" posts)
	if len(glob.glob('reddit_%s_*' % (post.id))) > 0:
		continue # we've already downloaded files for this reddit post


	if 'http://imgur.com/a/' in post.url:
		# This is an album post.
		albumId = post.url[len('http://imgur.com/a/'):]
		htmlSource = requests.get(post.url).text

		matches = list(frozenset(imagePattern.findall(htmlSource))) # turn this into a unique list using a frozenset
		for match in matches:
			if 'albumview.gif?a=' in match[0]:
				continue # this is not an actual image url

			response = requests.get(match[0])
			localFileName = 'reddit_%s_album_%s_imgur_%s' % (post.id, albumId, match[1])

			if response.status_code == 200:
				print('Downloading %s...' % (localFileName))
				with open(localFileName, 'wb') as fo:
					for chunk in response.iter_content(4096):
						fo.write(chunk)

	elif 'http://i.imgur.com/' in post.url:
		# The URL is a direct link to the image.
		response = requests.get(post.url)
		mo = imgurUrlPattern.search(post.url)

		imgurFilename = mo.group(2)
		if '?' in imgurFilename:
			# The regex doesn't catch a "?" at the end of the filename, so we remove it here.
			imgurFilename = imgurFilename[:imgurFilename.find('?')]
		localFileName = 'reddit_%s_album_None_imgur_%s' % (post.id, imgurFilename)

		if response.status_code == 200:
			print('Downloading %s...' % (localFileName))
			with open(localFileName, 'wb') as fo:
				for chunk in response.iter_content(4096):
					fo.write(chunk)

	elif 'http://imgur.com/' in post.url:
		# This is an Imgur page with a single image.
		htmlSource = requests.get(post.url).text # download the image's page
		mo = imgTagPattern.search(htmlSource)
		if mo is None:
			continue

		localFileName = 'reddit_%s_album_None_imgur_%s' % (post.id, mo.group(2))
		response = requests.get(mo.group(1))

		if response.status_code == 200:
			print('Downloading %s...' % (localFileName))
			with open(localFileName, 'wb') as fo:
				for chunk in response.iter_content(4096):
					fo.write(chunk)
