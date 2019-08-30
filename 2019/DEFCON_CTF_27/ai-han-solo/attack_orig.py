import hashlib, glob, os, random, re, requests, sys, requests, shutil, itertools
import tensorflow as tf
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image

from PIL import Image


host = sys.argv[1]
port = sys.argv[2]
base_url = "http://{}:{}".format(host, port)

image_path = "/home/xion/Desktop/GoN/DEFCON_2019/real/ai-han-solo/emnist-png/emnist-balanced"

# EXPLOIT parameters
possible_chars = "0123456789ABCDEF"
trials = 16

file_list = {}
for c in possible_chars:
    image_dir = os.path.join(image_path, c)
    file_list[c] = glob.glob(image_dir + "/*.png")

def create_image(hex_str):
    full_img = Image.new('1', (448, 28), color='black')

    for cnt, val in enumerate(hex_str):
        random_file = file_list[val][random.randint(0, len(file_list[val])-1)]
        img = Image.open(random_file)
        full_img.paste(img, (cnt*28,0))

    img_array = image.img_to_array(full_img)
    img_array = np.expand_dims(img_array, axis=0)

    return img_array


model_filename = 'navigation_parameters_{}.h5'.format(host)

model_file = requests.get('{}/navigation_parameters.h5'.format(base_url), stream=True)
with open(model_filename, 'wb') as f:
    model_file.raw.decode_content = True
    shutil.copyfileobj(model_file.raw, f)

model = load_model(model_filename)
model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

def eeval2(a, op):
    img = create_image(a)
    input_data = tf.get_default_graph().get_tensor_by_name('conv2d_1_input:0')

    tensor_name = 'dense_2/BiasAdd:0'
    outputs = tf.get_default_graph().get_tensor_by_name(tensor_name)
    sess = tf.keras.backend.get_session()

    classes = sess.run(outputs, feed_dict={input_data: img})
    if op is None:
        return list(map(float, classes[0]))
    else:
        return float(classes[0][op])

def hashtest(val):
    hash_test_range = 16
    hash_trials = 10
    if (np.argmax(model.predict(create_image(val))) != 16):
        return False
    for i in range(hash_test_range):
        success_count = 0
        val = hashlib.sha256(b"000-" + val.encode('latin1')).hexdigest().upper()[:16]
        for j in range(hash_trials):
            if (np.argmax(model.predict(create_image(val))) == 17 + i):
                success_count += 1
        if success_count < hash_trials * 0.8:
            return False
    return True

neuron_number = 16

def replace_n_char(flag, n, char):
    return flag[:n] + char + flag[n+1:]

pot = set()
current_flag = ''.join(random.sample(possible_chars, 16))
current_score = sum([eeval2(current_flag, None)[neuron_number] for _ in range(trials)]) / trials
try:
    for i in range(100):
        for j in range(1000):
            select_char = random.choice(possible_chars)
            select_idx = random.randint(0, 15)
            if current_flag[select_idx] == select_char:
                continue
            test_flag = replace_n_char(current_flag, select_idx, select_char)
            test_score = sum([eeval2(test_flag, None)[neuron_number] for _ in range(trials)]) / trials
            if test_score > current_score or random.random() < (100 / (j + 100 + i*10)) ** 4:
                current_flag, current_score = test_flag, test_score
                print("flag: {}, score: {}".format(current_flag, current_score))
                if hashtest(current_flag):
                    print("SOLVED!")
                    print(current_flag)
                    exit(0)
                if current_score > 0:
                    pot.add(current_flag)
                    print(len(pot))
except:
    pass

chset = [set() for _ in range(16)]
for st in pot:
    for i in range(16):
        chset[i].add(st[i])
for st in pot:
    chset[i] = list(chset[i])
for targ in itertools.product(*chset):
    current_flag = ''.join(targ)
    if hashtest(current_flag):
        print("SOLVED!")
        print(current_flag)
        exit(0)



"""
while True:
    current_flag = "11111111"
    for i in range(len(current_flag),16):
        maxv=([], -99999)
        for j in possible_chars:
            for k in range(trials):
                test_flag = current_flag + j
                score = eeval2(test_flag, 1)#neuron_number)
                if score > maxv[1]:
                    maxv = (0, score, j)

        current_flag += maxv[2]
        print(maxv[1])

    predict_res = model.predict(create_image(current_flag))
    print(current_flag[::-1], np.argmax(predict_res), predict_res[0][1])
    next_flag = hashlib.sha256(b"000-" + current_flag[::-1].encode('latin1')).hexdigest().upper()[:16]
    if (np.argmax(model.predict(create_image(current_flag))) == 16):
        if (np.argmax(model.predict(create_image(next_flag))) == 17):
            print(next_flag)
            break
"""
data = {"location": current_flag }
response = requests.post("{}/capture".format(base_url), data=data)
print(response.text.split('<p>')[-1].split('\n')[0].strip())

exit(0)