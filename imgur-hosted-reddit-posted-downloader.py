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
		MIN_SCORE = int(sys.argv[2])


imageInAlbumPattern = re.compile(r'<a href="(//i.imgur.com/(.*?))(\?.*?)?" target="_blank">View full resolution</a>')
imgTagPattern = re.compile(r'<img src="(http://i.imgur.com/(.*?))(\?.*?)?"')
imgurUrlPattern = re.compile(r'(http://i.imgur.com/(.*))(\?.*)?')


def downloadImage(response, localFileName):
	if response.status_code == 200:
		print('Downloading %s...' % (localFileName))
		with open(localFileName, 'wb') as fo:
			for chunk in response.iter_content(4096):
				fo.write(chunk)

# Connect to reddit and download the subreddit front page
r = praw.Reddit(user_agent='CHANGE THIS TO A UNIQUE VALUE') # Note: Be sure to change the user-agent to something unique.
submissions = r.get_subreddit(targetSubreddit).get_hot(limit=25)
# Or use one of these functions:
#                                       .get_top_from_year(limit=25)
#                                       .get_top_from_month(limit=25)
#                                       .get_top_from_week(limit=25)
#                                       .get_top_from_day(limit=25)
#                                       .get_top_from_hour(limit=25)
#                                       .get_top_from_all(limit=25)

# Process all the submissions from the front page
for submission in submissions:
	# Check for all the cases where we will skip a submission:
	if "imgur.com/" not in submission.url:
		continue # skip non-imgur submissions
	if submission.score < MIN_SCORE:
		continue # skip submissions that haven't even reached 100 (thought this should be rare if we're collecting the "hot" submission)
	if len(glob.glob('reddit_%s_%s_*' % (targetSubreddit, submission.id))) > 0:
		continue # we've already downloaded files for this reddit submission

	if 'http://imgur.com/a/' in submission.url:
		# This is an album submission.
		albumId = submission.url[len('http://imgur.com/a/'):]
		htmlSource = requests.get(submission.url).text

		matches = list(frozenset(imageInAlbumPattern.findall(htmlSource))) # turn this into a unique list using a frozenset
		for match in matches:
			if 'albumview.gif?a=' in match[0]:
				continue # this is not an actual image url

			response = requests.get('http:' + match[0])
			localFileName = 'reddit_%s_%s_album_%s_imgur_%s' % (targetSubreddit, submission.id, albumId, match[1])

			downloadImage(response, localFileName)

	elif 'http://i.imgur.com/' in submission.url:
		# The URL is a direct link to the image.
		response = requests.get(submission.url)
		mo = imgurUrlPattern.search(submission.url)

		imgurFilename = mo.group(2)
		if '?' in imgurFilename:
			# The regex doesn't catch a "?" at the end of the filename, so we remove it here.
			imgurFilename = imgurFilename[:imgurFilename.find('?')]
		localFileName = 'reddit_%s_%s_album_None_imgur_%s' % (targetSubreddit, submission.id, imgurFilename)

		downloadImage(response, localFileName)

	elif 'http://imgur.com/' in submission.url:
		# This is an Imgur page with a single image.
		htmlSource = requests.get(submission.url).text # download the image's page
		mo = imgTagPattern.search(htmlSource)
		if mo is None:
			continue

		localFileName = 'reddit_%s_%s_album_None_imgur_%s' % (targetSubreddit, submission.id, mo.group(2))
		response = requests.get(mo.group(1))

		downloadImage(response, localFileName)
