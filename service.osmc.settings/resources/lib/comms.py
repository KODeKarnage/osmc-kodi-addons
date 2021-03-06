# Standard modules
import socket
import threading
import os
import subprocess

# XBMC modules
import xbmc
import xbmcaddon
import xbmcgui

def log(message):
	xbmc.log('osmc_comms: ' + str(message))

class communicator(threading.Thread):

	def __init__(self, parent_queue, socket_file):

		# queue back to parent
		self.parent_queue = parent_queue

		# not sure I need this, but oh well
		#self.wait_evt = threading.Event()

		threading.Thread.__init__(self)

		self.daemon = True

		# create the listening socket, it creates new connections when connected to
		self.address = socket_file

		if os.path.exists(self.address):
			subprocess.call(['sudo', 'rm', self.address])
			try:
				# I need this for testing on my laptop
				os.remove(self.address)
			except:
				log('Connection failed to delete socket file.')
				pass

		self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

		# allows the address to be reused (helpful with testing)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.sock.bind(self.address)
		self.sock.listen(1)
		
		self.stopped = False


	def stop(self):
		''' Orderly shutdown of the socket, sends message to run loop
			to exit. '''

		try:

			log('Connection stopping.')
			self.stopped = True
			sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
			sock.connect(self.address)
			sock.send('exit')
			sock.close()
			self.sock.close()
				
		except Exception, e:

			log('Comms error trying to stop: {}'.format(e))

		try:
			os.remove(self.address)
		except:
			log('Comms error trying to delete socket: {}'.format(e))	

		log('Connection stop called')		


	def run(self):

		log('Comms started')

		while not xbmc.abortRequested and not self.stopped:

			# wait here for a connection
			conn, addr = self.sock.accept()

			log('Connection active.')

			# turn off blocking for this temporary connection
			# this will allow the loop to collect all parts of the message
			conn.setblocking(0)

			passed = False
			total_wait = 0
			wait = 5

			while not xbmc.abortRequested and not passed and total_wait < 500:
				try:
					data = conn.recv(8192)
					passed = True
					log('data = %s' % data)
				except:
					total_wait += wait
					xbmc.sleep(5)

			if not passed:
				log('Connection failed to collect data.')
				self.stopped = True
				conn.close()
				break

			log('data = %s' % data)

			# if the message is to stop, then kill the loop
			if data == 'exit':
				log('Connection called to "exit"')
				self.stopped = True
				conn.close()
				break

			# send the data to Main for it to process
			self.parent_queue.put(data)

			conn.close()

		log('Comms Ended')
