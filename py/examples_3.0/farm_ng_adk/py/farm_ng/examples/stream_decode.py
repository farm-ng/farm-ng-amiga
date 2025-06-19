from queue import Queue, Empty
import argparse
import asyncio
import av
import logging
import numpy as np
import threading

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, GdkPixbuf

from farm_ng import Amiga, nexus as apb

class StreamDecoder:
    def __init__(self, amiga: Amiga):
        """Initialize the StreamDecoder with H.264 codec and GTK display window.

        Args:
            amiga: The Amiga instance to use for video configuration
        """
        self.codec = av.CodecContext.create('h264', 'r')
        self.amiga = amiga
        self.config_queue = Queue()  # Regular Queue for thread communication

        self.frame_count = 0
        self.frame_queue = Queue(maxsize=2)
        self.running = True
        self.stop_event = asyncio.Event()
        self._waiting_message_shown = False

        # Initialize GTK window in the main thread
        self.window = Gtk.Window()
        self.window.connect('destroy', self._on_window_destroy)

        # Create vertical box for layout
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.window.add(vbox)

        # Create horizontal box for controls
        control_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        vbox.pack_start(control_box, False, False, 0)

        # Camera selection dropdown
        camera_store = Gtk.ListStore(str)
        for camera in [
                "Cam0MonoLeft", "Cam0MonoRight", "Cam0Color",
                "Cam1MonoLeft", "Cam1MonoRight", "Cam1Color"]:
            camera_store.append([camera])

        self.camera_combo = Gtk.ComboBox.new_with_model(camera_store)
        renderer_text = Gtk.CellRendererText()
        self.camera_combo.pack_start(renderer_text, True)
        self.camera_combo.add_attribute(renderer_text, "text", 0)
        self.camera_combo.set_active(0)  # Select first camera by default
        control_box.pack_start(self.camera_combo, True, True, 0)

        # Resolution selection dropdown
        resolution_store = Gtk.ListStore(str)
        for resolution in ["360p", "720p"]:
            resolution_store.append([resolution])

        self.resolution_combo = Gtk.ComboBox.new_with_model(resolution_store)
        renderer_text = Gtk.CellRendererText()
        self.resolution_combo.pack_start(renderer_text, True)
        self.resolution_combo.add_attribute(renderer_text, "text", 0)
        self.resolution_combo.set_active(0)  # Select 360p by default
        control_box.pack_start(self.resolution_combo, True, True, 0)

        # Apply button
        self.apply_button = Gtk.Button(label="Apply")
        self.apply_button.connect("clicked", self._on_apply_clicked)
        control_box.pack_start(self.apply_button, True, True, 0)

        # Image display
        self.image = Gtk.Image()
        vbox.pack_start(self.image, True, True, 0)

        self.window.show_all()

        # Start display thread
        logging.info("Starting display thread...")
        self.display_thread = threading.Thread(target=self._display_loop)
        self.display_thread.daemon = True
        self.display_thread.start()
        logging.info("Display thread started")

    def _get_selected_camera(self) -> str:
        """Get the currently selected camera from the dropdown."""
        tree_iter = self.camera_combo.get_active_iter()
        model = self.camera_combo.get_model()
        return model[tree_iter][0]

    def _get_selected_resolution(self) -> str:
        """Get the currently selected resolution from the dropdown."""
        tree_iter = self.resolution_combo.get_active_iter()
        model = self.resolution_combo.get_model()
        return model[tree_iter][0]

    def _on_apply_clicked(self, _):
        """Handle apply button click by queueing video stream configuration."""
        camera = self._get_selected_camera()
        resolution = self._get_selected_resolution()
        logging.info(f"Queueing video stream config: camera={camera}, resolution={resolution}")

        # Add the configuration request to the queue
        self.config_queue.put((camera, resolution))

    async def config_handler(self):
        """Handle video configuration requests from the GUI."""
        while self.running:
            try:
                # Non-blocking check for new configuration
                try:
                    camera, resolution = self.config_queue.get_nowait()
                    logging.info(f"Applying video stream config: camera={camera}, resolution={resolution}")
                    await self.amiga.select_video_stream(camera, resolution)
                except Empty:
                    pass

                # Sleep briefly to prevent busy-waiting
                await asyncio.sleep(0.1)
            except Exception as e:
                logging.error(f"Error configuring video stream: {e}")
                await asyncio.sleep(1.0)  # Wait longer on error

    def _on_window_destroy(self, _):
        """Handler for window close event"""
        logging.info("Window closed, stopping stream...")
        self.running = False
        self.stop_event.set()
        GLib.idle_add(Gtk.main_quit)  # Queue quit in main loop

    def _display_loop(self):
        """Thread for displaying frames"""
        logging.info("Display loop starting")
        while self.running:
            try:
                img = self.frame_queue.get(timeout=0.010)
                # Convert numpy array to GdkPixbuf
                height, width = img.shape[:2]
                pixbuf = GdkPixbuf.Pixbuf.new_from_data(
                    img.tobytes(),
                    GdkPixbuf.Colorspace.RGB,
                    False,
                    8,
                    width,
                    height,
                    width * 3
                )
                # Update image in main thread
                GLib.idle_add(self.image.set_from_pixbuf, pixbuf)
            except Empty:
                # Just continue waiting for frames
                continue
            except Exception as e:
                logging.error(f"Error in display loop: {e}")
                import traceback
                logging.error(traceback.format_exc())
                continue

    async def callback(self, stream: apb.Stream):
        try:
            frame_data = stream.video.data
            if not frame_data:
                return
            packets = self.codec.parse(frame_data)
            for packet in packets:
                frames = self.codec.decode(packet)
                for frame in frames:
                    img = frame.to_ndarray(format='rgb24')  # RGB for GTK
                    self.frame_count += 1
                    if not self.frame_queue.full():
                        self.frame_queue.put(img)
                    if self._waiting_message_shown:
                        logging.info("Found stream start!")
                        self._waiting_message_shown = False

        except av.error.InvalidDataError as e:
            logging.debug(f"Error decoding frame: {e}")
            if not self._waiting_message_shown:
                logging.info("Waiting for stream start..")
                self._waiting_message_shown = True
        except Exception as e:
            logging.error(f"Error: {e}")

    def cleanup(self):
        logging.info("Starting cleanup...")
        self.running = False
        self.stop_event.set()

        # Clear the frame queue
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except Empty:
                break

        # Wait for display thread
        if self.display_thread.is_alive():
            logging.info("Waiting for display thread...")
            self.display_thread.join(timeout=1.0)
            if self.display_thread.is_alive():
                logging.warning("Display thread did not terminate cleanly")

        # Cleanup codec
        del self.codec
        self.codec = None

        # Ensure GTK main loop is quit
        GLib.idle_add(Gtk.main_quit)

        logging.info(f"Cleanup completed: processed {self.frame_count} frames")

async def main(address: str):
    logging.info(f"Starting stream decoder")
    amiga = Amiga(address=address)
    handler = StreamDecoder(amiga)

    logging.info(f"Connecting to Amiga at {address}")
    await amiga.select_video_stream("Cam0MonoLeft", "360p")

    try:
        async with amiga.stream_sub(handler.callback):
            logging.info("Started streaming...")

            # Run GTK main loop in the main thread
            def gtk_main():
                try:
                    Gtk.main()
                except Exception as e:
                    logging.error(f"GTK error: {e}")
                    handler.stop_event.set()

            # Start GTK main loop in a separate thread
            gtk_thread = threading.Thread(target=gtk_main)
            gtk_thread.daemon = True
            gtk_thread.start()

            # Start configuration handler
            config_task = asyncio.create_task(handler.config_handler())

            # Wait until Ctrl+C or window close
            try:
                await handler.stop_event.wait()
            except KeyboardInterrupt:
                logging.info("Stopping stream...")
                handler.running = False
                GLib.idle_add(Gtk.main_quit)
            finally:
                handler.cleanup()
                # Cancel config handler task
                config_task.cancel()
                try:
                    await config_task
                except asyncio.CancelledError:
                    pass
                # Wait a bit for GTK thread to finish
                gtk_thread.join(timeout=1.0)

        logging.info("Streaming session completed successfully.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        force=True
    )

    parser = argparse.ArgumentParser(
        description="Connect to Amiga and displays decoded camera video"
    )
    parser.add_argument(
        "--address",
        type=str,
        default="127.0.0.1",
        help="IP address or hostname of the Amiga robot"
    )

    args = parser.parse_args()
    asyncio.run(main(args.address))
