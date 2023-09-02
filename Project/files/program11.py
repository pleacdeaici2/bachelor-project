import asyncio

async def sleep_coroutine():
    print("Start sleep")

    await asyncio.sleep(10)
    print("After sleep")


if __name__ == '__main__':
    # Create a new event loop
    loop = asyncio.new_event_loop()

    # Set the new event loop as the current event loop
    asyncio.set_event_loop(loop)

    # Run the coroutine
    loop.run_until_complete(sleep_coroutine())

    # Close the event loop
    loop.close()