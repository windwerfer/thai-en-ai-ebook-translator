import time

# Initialize a global variable to store the start time
start_time = None

def timer_start():
    global start_time
    # Record the current time when the function is called
    start_time = time.time()
    return start_time

def timer_end():
    global start_time
    # Calculate the elapsed time in milliseconds
    end_time = time.time()
    elapsed_time = (end_time - start_time)
    return elapsed_time

def elaplsed():
    global start_time
    # Calculate the elapsed time in milliseconds
    end_time = time.time()
    elapsed_time = (end_time - start_time)
    return timer_format(elapsed_time)

def timer_format(elapsed_seconds):
    # Format the time into HH:MM:SS
    hours = int(elapsed_seconds // 3600)
    minutes = int((elapsed_seconds % 3600) // 60)
    seconds = int(elapsed_seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"