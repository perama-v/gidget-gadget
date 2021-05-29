import random
import curses
import time
import bisect
import itertools

# Initialize screen
sc = curses.initscr()  # get curses window object.
h, w = sc.getmaxyx()  # get height and width of terminal.
win = curses.newwin(h, w, 0, 0)  # create curses window instance.
win.keypad(1)  # accept all keypad input.
# win.nodelay(True) # True = non-blocking behavriour
curses.curs_set(0)  # make cursor invisible.

# Locations, dimensions and positions
x_offset = 4  # Dist: x -> window bottom.
lr_margin = 4  # Space between the left and right walls and elements.
x_loc = h - x_offset  # y coord of the graphs horizontal axis.
y_head = 4  # Dist: y -> window top.
y_len = h - (y_head + x_offset + 1)  # Length of y axis.
bf_yloc = y_head + y_len//2  # y coord of basefee start pos.
block_width = 8  # Character width of a steady-state block.
bf_line = '-'  # Block starting appearance
bf_notch = w//2 + block_width + 1  # xloc of center of basefee padddle

# General parameters
block_gas = 15000000 # 15mil at steady state.
gas_per_char = block_gas // block_width  # How much gas one character represents.
gas_per_tx = 100000  # Fixed (~150tx per block at 15mill gas blocks).
txs_per_char = gas_per_char // gas_per_tx  # Num txs that fit in one character.
mem_width = w//2 - (block_width * 2 + lr_margin)  # Number of characters wide the mempool is.
block_time = 3  # Seconds per block.
block_made = False  # Detect if need to build a block
rescale_trigger = 0.3  # Rescale y ax if basefee gets within this fraction from either end.

# Initial conditions
snake_head = [3,15]
snake_position = [[15,3],[14,3],[13,3]]
apple_position = [20,20]
score = 0

mem_txs = []  # Mempool transaction prices in Gwei.
mem_bars_mean = []  # Average tx gas price in each mempool column.
mem_bars_max = []  # Max tx gas price in each mempool column.
max_gwei = 100  # Max Gwei displayed on y-axis.
basefee = 50  # Starting Basefee.
num_projections = 24  # Number of projections to graph.
proj_up = []  # Max projected basefee changes.
proj_down = []  # Min rojected basefee changes.
prog_start = True  # Starting condition.

prev_button_direction = 1
button_direction = 1
key = curses.KEY_RIGHT
numpad = [ord(str(i)) for i in range(10)]  # For number 1: numpad[1] = 49.
gwei_zeros = 10  # Five if pressed: 10 = 50 Gwei, 100 = 500 Gwei.

def get_gwei_loc(gwei):
    # Finds y coord of given gwei
    gwei_frac_from_top = (max_gwei - gwei) / max_gwei
    portion_y_len = y_len * gwei_frac_from_top
    y_loc = int(y_head + portion_y_len)
    return y_loc

def pack_txs(mem_txs):
    # Groups txs into what fits in slots one-character wide.
    # Calculates average gas price

    bucket_list_mean = []  # average gas price in each group
    bucket_list_max = []  # max tx gas price in each group

    for i in range(0, len(mem_txs), txs_per_char):
        #  Go through txs is chucks as large as one-character
        group = mem_txs[::-1][i: i+10]
        average = int(sum(group)/len(group))
        bucket_list_mean.append(average)
        bucket_list_max.append(group[0])
    # Return buckets, ordered large to small
    return bucket_list_mean, bucket_list_max

def get_projections(basefee, upward=True):
    # Calculates projected max/min basefees and returns their y coords.
    # Fee = Fee + (or -) Fee * 1/8
    # Fee *= (9/8)**n or Fee *= (7/8)**n
    factor = 9/8
    if not upward:
        factor = 7/8
    fee_loc_array = [(basefee * pow(factor,i+1)) for i in range(num_projections)]
    return fee_loc_array

while True:
    win.border(0)
    win.timeout(100)



    next_key = win.getch()

    if next_key == -1:
        key = key
    else:
        key = next_key

    if key == ord('q'):
        break
    elif key in numpad and key != 48 :  # Ignore zero
        selected_gwei = numpad.index(key) * gwei_zeros # Desired gwei.
        pos = bisect.bisect(mem_txs, selected_gwei)  # index to put new txs.
        new_txs = [selected_gwei] * 10  # new txs.
        mem_txs = mem_txs[:pos] + new_txs + mem_txs[pos:]  # add to mempool.
        mem_bars_mean, mem_bars_max = pack_txs(mem_txs)  # get new mempool bars for graph

        key = -1
        win.clear()
    else:
        pass


    # Make block
    if int(time.time()) % block_time == 0 or prog_start:
        if not block_made:
            # construct_block()
            basefee *= 7/8
            proj_up = get_projections(basefee, upward = True)
            proj_down = get_projections(basefee, upward = False)
            if basefee >= (1 - rescale_trigger) * max_gwei:
                max_gwei = 2 * basefee  # Set basefee to middle of axis.
            if basefee <= (rescale_trigger) * max_gwei:
                max_gwei = 2 * basefee  # Set basefee to middle of axis.
            bf_yloc = get_gwei_loc(basefee)
            block_made = True
            bf_line = '='  # Change appearance of block
            win.clear()
            prog_start = False
    else:
        if block_made:
            # Return to inter-block appearance
            bf_line = '-'
            block_made = False
            win.clear()



    # Calc fee
    #basefee *= updown / 8



    # display dynamic elements
    win.vline(bf_yloc-2, bf_notch, '>',2)  # basefee paddle steady-state notch.
    win.hline(bf_yloc, w//2+1 , bf_line, block_width * 2)  # basefee paddle.
    win.addstr(y_head+1, w//2 - 4, str(int(max_gwei)))  # Y-axis max gwei.
    win.addstr(bf_yloc, w//2 - 4 , str(int(basefee)))  # basefee.
    if mem_bars_mean != []:
        for i in range(min(len(mem_bars_mean),mem_width)):
            max_mem_tip = get_gwei_loc(min(mem_bars_max[i], max_gwei))
            # Draw mempool txs
            win.vline(max_mem_tip, w//2+block_width*2+i , '*', x_loc - max_mem_tip) # Max
            mean_mem_tip = get_gwei_loc(min(mem_bars_mean[i], max_gwei))
            win.vline(mean_mem_tip, w//2+block_width*2+i , "T", x_loc - mean_mem_tip) # Mean


    for i in range(num_projections):
        proj_num = str(i+1)
        if i>8:
            proj_num = '-'
        win.hline(get_gwei_loc(proj_down[i]), w//2+1+block_width*2+i,
            proj_num, 1)  # Downward projections.
        elem_start = int(w//2+1+block_width*2*(i+1))
        # If element is within window.
        if proj_up[i] < max_gwei and elem_start + block_width*2 <= (w - lr_margin):
            # Upward projections
            win.hline(get_gwei_loc(proj_up[i]), elem_start, '~', block_width * 2)
            win.hline(get_gwei_loc(proj_up[i]), elem_start + block_width, proj_num, 1)



    # display static elements
    win.vline(y_head, w//2, '^', 1)  # y-arrowhead.
    win.vline(y_head + 1, w//2, '|', y_len)  # y ax.
    win.hline(x_loc, lr_margin , '-', w - lr_margin * 2)  # x ax


sc.addstr(h//2, w//2, 'Bye-o!')
sc.refresh()
time.sleep(2)
curses.endwin()
