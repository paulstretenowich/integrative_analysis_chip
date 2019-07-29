from utilsm import *
import os
import sys



def findfiles(base, pattern):
	cmd = "find {0} -iname '{1}'".format(base, pattern)
	print cmd
	p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	return [e.strip() for e in p.stdout.readlines()]

def listfiles(base):
	p = subprocess.Popen("find {0}  -type f".format(base), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	return [e.strip() for e in p.stdout.readlines()]


def flistsize(fs):
	return {e : os.stat(e).st_size for e in fs}

def byino(fs):
	hashed = dict()
	for e in fs:
		ino = os.stat(e).st_ino 
		if not ino in hashed: hashed[ino] = list()
		hashed[ino].append(e)
	hashed2 = dict()
	full_flist = dict()
	for k,v in hashed.items():
		sortedfiles = sorted(v, key = lambda x: (len(x),  os.path.basename(x)) )
		hashed2[k] =  sortedfiles[0]
		assert not sortedfiles[0] in full_flist
		full_flist[sortedfiles[0]] = sortedfiles[1:]
	return (hashed2, full_flist)

def md5script(hashed):
	def cmd(f):
		if f.strip().endswith('bam'):
			return 'echo "{1} $(./headlessbam_md5 {0})"'.format(f, os.path.basename(f))
		else:
			return 'echo "{1} $(md5sum {0})"'.format(f, os.path.basename(f))
			
	return [cmd(v) for v in sorted(hashed.values(), key= lambda x: os.path.basename(x))]

def trackoutput(base, i, filereport):
	logerr('# looking in {0}\n'.format(base))
	bams = findfiles(base, '*.bam')
	narrowpeaks = findfiles(base, '*narrow*gz')
	(bamsbyino, bams_flist) = byino(bams)
	(peaksbyino, peaks_flist) = byino(narrowpeaks)

	if not filereport:
		print writef('./computemd5s_{0}'.format(i),  ['#!/bin/bash'] + md5script(bamsbyino) + md5script(peaksbyino)) 
	
	qc = findfiles(base, 'qc.html')	
	print qc

	return { 'bams' : bams_flist, 'peaks' : peaks_flist, 'qc' : byino(qc)[1] }



def make_filereport(patterns, base):
	logerr('# looking in {0}\n'.format(base))
	fbyino, flist = dict(), dict()
	for p in patterns:
		found = findfiles(base, p)
		(a, b) = byino(found)
		fbyino[p] = a
		flist[p] = b	
	return {'byino' : fbyino, 'flist':flist}	


def main(args):
	filereport = True
	assert len(args) == 1, '__only_one_target_directory_at_a_time__'

	arg = args[0]
		
	config = jloadf('cleanup.json')
	patterns = config["patterns"]
	assert not "extra" in patterns
	output = make_filereport(patterns, arg) 
	short_out = {k: sorted(output['flist'][k].keys()) for k in output['flist']}
	allfiles = listfiles(arg)


	

	patternfiles = list()
	for p in patterns:
		record = output
		print p, sum(flistsize(record['flist'][p]).values())/10**9,  'GB approx'
		patternfiles.extend(record['flist'][p].keys() +  [e for k in record['flist'][p]  for e in record['flist'][p][k]]    ) 

	
	extra = [f for f in allfiles if not f in patternfiles]

	print jdumpf('./filereport.json', output)
	print jdumpf('./file_shortreport.json', short_out)
	
	rmlist = list()
	for ftype in config["delete"]:
		for k in record['flist'][ftype]:
			rmlist.extend(record['flist'][ftype][k])
			rmlist.append(k)

	keep = list()
	for k in record['flist']:
		if not k in config['delete']:
			keep.extend([e for e in  record['flist'][k].keys() if not e in rmlist])
	keep = sorted(list(set(keep)))


	print dumpf('./delete.list', '\n'.join(rmlist) + '\n')	
	print dumpf('./masterfiles.list', '\n'.join(keep) + '\n')
	print jdumpf('./unrecognized_files.json', extra)

	#print 'size',  sum(flistsize(keep).values())
	
	

if __name__ == '__main__':
	main(sys.argv[1:])



