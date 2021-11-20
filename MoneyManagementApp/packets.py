import rsa
import json
import base64

#endpoint for API
end_point_address="34.94.45.224:80"

#rsa encryption method
def encryption(data, encrypt=True, pubkey="pubkey", privkey="privkey"):
	if encrypt == True:
		with open(pubkey,"rb") as f:
			key = f.read()
			pubkey = rsa.PublicKey.load_pkcs1(key)
			if type(data) == bytes:
				encoded_message = rsa.encrypt(data, pubkey)
				return encoded_message
			else:
				encoded_message = rsa.encrypt(data.encode(), pubkey)
				return encoded_message
	elif encrypt == False:
		with open(privkey,"rb") as f:
			key = f.read()
			privkey = rsa.PrivateKey.load_pkcs1(key)
			decoded_message = rsa.decrypt(data, privkey).decode()
		return decoded_message


#create pair of rsa keys
def create_keys_rsa(username):
	public_key, private_key = rsa.newkeys(2048)
	with open(f"{username}_pubkey", "w") as f:
		f.write(public_key.save_pkcs1().decode('utf-8'))
	
	with open(f"{username}_privkey", "w") as f:
		f.write(private_key.save_pkcs1().decode('utf-8'))
	return public_key, private_key


def build_packet(data, user=False):
	packet = {}
	if user == True:
		for key in data:
			packet[key] = base64.b64encode(encryption(str(data[key]), pubkey=f"{user}_pubkey", privkey=f"{user}_privkey")).decode()
		return json.dumps(packet)
	elif user == False:
		for key in data:
			packet[key] = base64.b64encode(encryption(str(data[key]))).decode()
		return json.dumps(packet)


def recieve_packet(data, user=False):
	packet = {}
	if user == True:
		for key in data:
			packet[key] = encryption(base64.b64decode(data[key]), encrypt=False, privkey=f"{user}_privkey")
		return packet
	elif user == False:
		for key in data:
			packet[key] = encryption(base64.b64decode(data[key]), encrypt=False)
		return packet