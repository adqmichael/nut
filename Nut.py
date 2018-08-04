#!/usr/bin/python3
# -*- coding: utf-8 -*-
# place this file in your CDNSP directory
# add the following line to the top of your CDNSP.py file:
# from tqdm import tqdm

import argparse
import sys
import os
import re
import pathlib
import urllib3
import json
from Title import Title
import Titles
import Nsp
import Nsps
import CDNSP
import Config
#import blockchain

				
def loadTitleWhitelist():
	global titleWhitelist
	titleWhitelist = []
	with open('whitelist.txt', encoding="utf8") as f:
		for line in f.readlines():
			titleWhitelist.append(line.strip().upper())
			
def loadTitleBlacklist():
	global titleBlacklist
	titleBlacklist = []
	with open('blacklist.txt', encoding="utf8") as f:
		for line in f.readlines():
			titleBlacklist.append(line.strip().upper())
			
def logMissingTitles():
	f = open("missing.txt","w+b")
	
	for k,t in Titles.items():
		if not t.path:
			f.write((t.name + "\r\n").encode("utf-8"))
		
	f.close()
	
def update_db(dbURL):
	global titlekey_list
	print("\nDownloading new titlekey database...\n")
	try:
		url = dbURL
		if url == '':
			print('\nDatabase url is empty. Check the CDNSPconfig')
			return
		if "http://" not in url and "https://" not in url:
			try:
				url = base64.b64decode(url)
			except Exception as e:
				print("\nError decoding url: ", e)
				return

		r = requests.get(url)
		r.encoding = 'utf-8'

		if r.status_code == 200:
			newdb = r.text.split('\r')

			currdb = [x.strip() for x in titlekey_list]
			print('The following games have either been added or updated:\n')
			for line in newdb:
				line = line.strip()
				if line != '':
					temp = line.split('|')
					titleId = temp[0][0:16]
					tkey = temp[1].lower()
					name = temp[2]
					line = '%s|%s|%s' % (titleId,tkey,name)
					if line not in currdb and line != None :
						print(line.split('|')[-1])

			try:
				print('\nSaving new database...')
				f = open('titlekeys.txt', 'w', encoding="utf8")
				for line in newdb:
					f.write(line)
				f.close()
				print('\nDatabase update complete')
				titlekey_list = []
				load_titlekeys()
			except Exception as e:
				print(e)
				return
		else:
			print('Error updating database: ', repr(r))
			return
			
	except Exception as e:
		print('\nError updating database:', e)
		return
	
def downloadAll():
	for k,t in Titles.items():
		if not t.path and (not t.isDLC or Config.downloadDLC) and (not t.isDemo or Config.downloadDemo) and (t.key or Config.downloadSansTitleKey) and (len(titleWhitelist) == 0 or t.id in titleWhitelist) and t.id not in titleBlacklist:
			if not t.id:
				print('no valid id? ' + str(t.path))
				continue
				
			if not t.lastestVersion():
				print('Could not get version for ' + t.name)
				continue
				
			print('Downloading ' + t.name + ', ' + str(t.version).lower())
			CDNSP.download_game(t.id.lower(), t.lastestVersion(), t.key, True, '', True)
			
def export(file):
	with open(file, 'w', encoding='utf-8') as csv:
		csv.write('id|rightsId|key|isUpdate|isDLC|isDemo|name|version\n')
		for k,t in Titles.items():
			csv.write(str(t.id or '0000000000000000') + '|' + str(t.rightsId or '00000000000000000000000000000000') + '|' + str(t.key or '00000000000000000000000000000000') + '|' + str((t.updateId == t.id)*1) + '|' + str(t.isDLC*1) + '|' + str(t.isDemo*1)+ '|' + str(t.name or '') + '|' + str(t.version or '') + '\n')

def scan():
	Nsps.scan(Config.scanPath)
	Titles.save()
	
def organize():
	scan()
	for f in Nsps.files:
		#print('')
		f.move()
	print('removing empty directories')
	Nsps.removeEmptyDir('.', False)
		
def refresh():
	for f in Nsps.files:
		try:
			f.readMeta()
		except:
			raise
			pass
	Titles.save()
			
if __name__ == '__main__':
	titleWhitelist = []
	titleBlacklist = []

	Titles.load()
		

	urllib3.disable_warnings()


	CDNSP.tqdmProgBar = False
	CDNSP.configPath = os.path.join(os.path.dirname(__file__), 'CDNSPconfig.json')

	if os.path.isfile(CDNSP.configPath):
		CDNSP.hactoolPath, CDNSP.keysPath, CDNSP.NXclientPath, CDNSP.ShopNPath, CDNSP.reg, CDNSP.fw, CDNSP.deviceId, CDNSP.env, CDNSP.dbURL, CDNSP.nspout = CDNSP.load_config(CDNSP.configPath)
	else:
		Config.downloadBase = False
		Config.downloadDLC = False
		Config.downloadDemo = False
		Config.downloadSansTitleKey = False
		Config.downloadUpdate = False

	if CDNSP.keysPath != '':
		CDNSP.keysArg = ' -k "%s"' % CDNSP.keysPath
	else:
		CDNSP.keysArg = ''

	loadTitleWhitelist()
	loadTitleBlacklist()

	parser = argparse.ArgumentParser()
	parser.add_argument('--base', type=bool, choices=[0, 1], default=Config.downloadBase*1, help='download base titles')
	parser.add_argument('--demo', type=bool, choices=[0, 1], default=Config.downloadDemo*1, help='download demo titles')
	parser.add_argument('--update', type=bool, choices=[0, 1], default=Config.downloadUpdate*1, help='download title updates')
	parser.add_argument('--dlc', type=bool, choices=[0, 1], default=Config.downloadDLC*1, help='download DLC titles')
	parser.add_argument('--nsx', type=bool, choices=[0, 1], default=Config.downloadSansTitleKey*1, help='download titles without the title key')
	parser.add_argument('-d', '--download', help='download title(s)')
	parser.add_argument('-i', '--info', help='show info about title or file')
	parser.add_argument('-s', '--scan', action="store_true", help='scan for new NSP files')
	parser.add_argument('-o', '--organize', action="store_true", help='rename and move all NSP files')
	parser.add_argument('-r', '--refresh', action="store_true", help='reads all meta from NSP files and queries CDN for latest version information')
	parser.add_argument('-x', '--export', help='export title database in csv format')
	
	args = parser.parse_args()
	

	Config.downloadBase = args.base
	Config.downloadDLC = args.dlc
	Config.downloadDemo = args.demo
	Config.downloadSansTitleKey = args.nsx
	Config.downloadUpdate = args.update
	
	if args.scan:
		scan()
		
	if args.refresh:
		refresh()
	
	if args.organize:
		organize()
		
	if args.download:
		downloadAll()
		
	if args.export:
		export(args.export)
		
	if len(sys.argv)==1:
		scan()
		organize()
		downloadAll()
	
	#scan()
		
	#logMissingTitles()

	#downloadAll()

	#Titles.save()