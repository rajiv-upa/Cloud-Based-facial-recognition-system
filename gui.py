import tkinter as tk
from tkinter import ttk, messagebox
import boto3
import io
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os
from datetime import datetime
import csv
import pandas as pd
import cv2
import numpy as np
from tkcalendar import DateEntry

class ModernButton(tk.Button):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(
            relief=tk.FLAT,
            font=('Helvetica', 10, 'bold'),
            padx=15,
            pady=8,
            cursor='hand2'
        )
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)

    def on_enter(self, e):
        if self['state'] != 'disabled':
            self['background'] = self.darker(self['background'])

    def on_leave(self, e):
        if self['state'] != 'disabled':
            self['background'] = self.lighter(self['background'])

    def darker(self, color):
        rgb = self.winfo_rgb(color)
        return f'#{int(rgb[0]/256*0.8):02x}{int(rgb[1]/256*0.8):02x}{int(rgb[2]/256*0.8):02x}'

    def lighter(self, color):
        rgb = self.winfo_rgb(color)
        return f'#{int(min(rgb[0]/256*1.2, 255)):02x}{int(min(rgb[1]/256*1.2, 255)):02x}{int(min(rgb[2]/256*1.2, 255)):02x}'

class FaceRecognitionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Face Recognition System")
        self.root.geometry("1200x700")
        self.root.configure(bg='#f0f0f0')
        
        # Color scheme
        self.colors = {
            'primary': '#2196F3',    # Blue
            'secondary': '#4CAF50',  # Green
            'warning': '#FFC107',    # Yellow
            'danger': '#F44336',     # Red
            'bg': '#f0f0f0',        # Light gray
            'text': '#333333',      # Dark gray
            'white': '#FFFFFF',
            'info': '#4CAF50'       # Green
        }
        
        # Variables
        self.cap = None
        self.is_camera_on = False
        self.current_frame = None
        self.last_capture_time = None
        self.date_picker = None
        self.attendance_file = None
        
        # Set attendance directory using absolute path
        self.attendance_dir = os.path.abspath("attendance")
        
        # Ensure attendance directory exists with proper permissions
        self.ensure_directory_access()
        
        # Create default camera icon
        self.create_camera_icon()
        
        # Admin credentials
        self.admin_username = "admin"
        self.admin_password = "pass123"
        
        try:
            # Initialize AWS clients with proper error handling
            session = boto3.Session(region_name='us-east-1')
            self.rekognition = session.client('rekognition')
            self.dynamodb = session.client('dynamodb')
            
            # Test AWS connectivity
            self.test_aws_connection()
            
        except Exception as e:
            messagebox.showerror("AWS Configuration Error", 
                               f"Failed to initialize AWS services. Please check your credentials and internet connection.\nError: {str(e)}")
            root.destroy()
            return
        
        # Create widgets first
        self.create_widgets()
        self.apply_styles()
        
        # Initialize attendance file after widgets are created
        self.init_attendance_file()

    def ensure_directory_access(self):
        """Ensure the attendance directory exists and is accessible"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.attendance_dir, exist_ok=True)
            
            # Test write permissions by creating and removing a test file
            test_file = os.path.join(self.attendance_dir, 'test_permissions.txt')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                self.update_results("✅ Attendance directory is ready")
            except Exception as e:
                error_msg = f"Cannot write to attendance directory: {self.attendance_dir}\nError: {str(e)}"
                self.update_results(f"❌ {error_msg}")
                messagebox.showerror("Permission Error", error_msg)
                raise Exception("Directory permission error")
                
        except Exception as e:
            if not isinstance(e, Exception) or str(e) != "Directory permission error":
                error_msg = f"Failed to create/access attendance directory: {self.attendance_dir}\nError: {str(e)}"
                self.update_results(f"❌ {error_msg}")
                messagebox.showerror("Directory Error", error_msg)
            raise

    def init_attendance_file(self):
        try:
            if self.date_picker is None:
                today = datetime.now()
                self.attendance_file = os.path.join(self.attendance_dir, f"attendance_{today.strftime('%Y-%m-%d')}.csv")
            else:
                selected_date = self.date_picker.get_date()
                self.attendance_file = os.path.join(self.attendance_dir, f"attendance_{selected_date.strftime('%Y-%m-%d')}.csv")
            
            # Ensure directory exists and is writable
            self.ensure_directory_access()
            
            # Create file with headers only if it doesn't exist
            if not os.path.exists(self.attendance_file):
                try:
                    with open(self.attendance_file, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(['Name', 'Date', 'Time'])
                except PermissionError:
                    messagebox.showerror(
                        "Permission Error",
                        f"Cannot create attendance file. Please check file permissions for:\n{self.attendance_file}"
                    )
                    return False
            return True
            
        except Exception as e:
            self.update_results(f"Error initializing attendance file: {str(e)}")
            return False

    def mark_attendance(self, name):
        try:
            if self.date_picker is None:
                selected_date = datetime.now()
            else:
                selected_date = self.date_picker.get_date()
            
            # Format date as string
            date_str = selected_date.strftime('%Y-%m-%d')
            self.attendance_file = os.path.join(self.attendance_dir, f"attendance_{date_str}.csv")
            
            # Create directory if it doesn't exist
            os.makedirs(self.attendance_dir, exist_ok=True)
            
            # Create file with headers if it doesn't exist
            if not os.path.exists(self.attendance_file):
                with open(self.attendance_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Name', 'Date', 'Time'])
            
            # Append attendance
            current_time = datetime.now().strftime('%H:%M:%S')
            with open(self.attendance_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([name, date_str, current_time])
            
            self.update_results(f"✅ Marked attendance for {name} on {date_str} at {current_time}")
            return True
            
        except Exception as e:
            self.update_results(f"Error marking attendance: {str(e)}")
            return False

    def show_attendance_summary(self):
        try:
            selected_date = self.date_picker.get_date()
            date_str = selected_date.strftime('%Y-%m-%d')
            attendance_file = os.path.join(self.attendance_dir, f"attendance_{date_str}.csv")
            
            if not os.path.exists(attendance_file):
                self.update_results(f"No attendance records found for {date_str}")
                return
            
            try:
                # Read CSV file
                df = pd.read_csv(attendance_file)
                
                # Convert Date column to datetime and format it
                if 'Date' in df.columns and not df.empty:
                    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
                
                if df.empty:
                    self.update_results(f"No attendance records found for {date_str}")
                    return
                
                # Filter records for selected date
                df_date = df[df['Date'] == date_str]
                
                if df_date.empty:
                    self.update_results(f"No attendance records found for {date_str}")
                    return
                
                summary = f"Attendance Summary for {date_str}:\n\n"
                for _, row in df_date.iterrows():
                    summary += f"{row['Name']}: {row['Time']}\n"
                
                total_present = len(df_date)
                summary += f"\nTotal Present: {total_present}"
                
                self.update_results(summary)
                
            except Exception as e:
                self.update_results(f"Error reading attendance file: {str(e)}")
            
        except Exception as e:
            self.update_results(f"Error showing attendance summary: {str(e)}")

    def apply_styles(self):
        style = ttk.Style()
        style.configure('Title.TLabel', 
                       font=('Helvetica', 16, 'bold'), 
                       foreground=self.colors['text'],
                       background=self.colors['bg'])
        
        style.configure('Subtitle.TLabel', 
                       font=('Helvetica', 12),
                       foreground=self.colors['text'],
                       background=self.colors['bg'])
        
        style.configure('Status.TLabel',
                       font=('Helvetica', 10),
                       foreground=self.colors['text'],
                       background=self.colors['bg'])
        
        # Add new styles for admin UI
        style.configure('Admin.TFrame',
                       background=self.colors['bg'])
        
        style.configure('Admin.TLabel',
                       font=('Helvetica', 10),
                       foreground=self.colors['text'],
                       background=self.colors['bg'])
        
        style.configure('AdminTitle.TLabel',
                       font=('Helvetica', 16, 'bold'),
                       foreground=self.colors['text'],
                       background=self.colors['bg'])
        
        style.configure('AdminSubtitle.TLabel',
                       font=('Helvetica', 12, 'bold'),
                       foreground=self.colors['text'],
                       background=self.colors['bg'])
        
    def create_widgets(self):
        # Main container
        self.main_container = tk.Frame(self.root, bg=self.colors['bg'])
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_frame = tk.Frame(self.main_container, bg=self.colors['bg'])
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(title_frame, 
                 text="Face Recognition System", 
                 style='Title.TLabel').pack(side=tk.LEFT)
        
        # Status indicator
        self.status_label = ttk.Label(title_frame, 
                                    text="Camera: OFF", 
                                    style='Status.TLabel')
        self.status_label.pack(side=tk.RIGHT)
        
        # Content frame
        content_frame = tk.Frame(self.main_container, bg=self.colors['bg'])
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left frame (Camera)
        left_frame = tk.Frame(content_frame, bg=self.colors['white'], bd=1, relief=tk.SOLID)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Camera title
        ttk.Label(left_frame, 
                 text="Camera Feed", 
                 style='Subtitle.TLabel').pack(pady=10)
        
        # Camera display (with border)
        self.camera_container = tk.Frame(left_frame, bg=self.colors['text'], bd=1, relief=tk.SOLID)
        self.camera_container.pack(padx=10, pady=5)
        
        self.camera_label = ttk.Label(self.camera_container)
        self.camera_label.pack(padx=2, pady=2)
        # Show camera icon initially
        self.camera_label.configure(image=self.camera_icon)
        self.camera_label.image = self.camera_icon
        
        # Camera controls
        controls_frame = tk.Frame(left_frame, bg=self.colors['white'])
        controls_frame.pack(fill=tk.X, pady=15, padx=10)
        
        self.camera_btn = ModernButton(
            controls_frame,
            text="▶ Start Camera",
            command=self.toggle_camera,
            background=self.colors['primary'],
            foreground=self.colors['white']
        )
        self.camera_btn.pack(side=tk.LEFT, padx=5)
        
        self.capture_btn = ModernButton(
            controls_frame,
            text="📸 Capture & Recognize",
            command=self.capture_and_recognize,
            state='disabled',
            background=self.colors['secondary'],
            foreground=self.colors['white']
        )
        self.capture_btn.pack(side=tk.LEFT, padx=5)
        
        # Add View Attendance button
        self.view_btn = ModernButton(
            controls_frame,
            text="📋 View Attendance",
            command=self.show_attendance_summary,
            background=self.colors['info']
        )
        self.view_btn.pack(side=tk.LEFT, padx=5)
        
        # Right frame (Results)
        right_frame = tk.Frame(content_frame, bg=self.colors['white'], bd=1, relief=tk.SOLID)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # Results title
        ttk.Label(right_frame, 
                 text="Recognition Results", 
                 style='Subtitle.TLabel').pack(pady=10)
        
        # Results text area with custom font and colors
        self.results_text = tk.Text(
            right_frame,
            height=20,
            width=40,
            font=('Consolas', 11),
            bg=self.colors['white'],
            fg=self.colors['text'],
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Last capture time label
        self.time_label = ttk.Label(
            right_frame,
            text="Last capture: Never",
            style='Status.TLabel'
        )
        self.time_label.pack(pady=(0, 10))
        
        # Add date picker frame
        self.date_frame = ttk.Frame(right_frame)
        self.date_frame.pack(pady=5, fill='x')
        
        # Date label
        ttk.Label(self.date_frame, text="Select Date:").pack(side='left', padx=5)
        
        # Date picker
        self.date_picker = DateEntry(self.date_frame, width=12, background='darkblue',
                                   foreground='white', borderwidth=2,
                                   date_pattern='yyyy-mm-dd')
        self.date_picker.pack(side='left', padx=5)
        
        # View attendance button
        self.view_btn = ModernButton(
            self.date_frame,
            text="View Attendance",
            command=self.show_attendance_summary,
            background=self.colors['info']
        )
        self.view_btn.pack(side='left', padx=5)
        
        # Add admin controls frame
        admin_frame = ttk.Frame(right_frame)
        admin_frame.pack(pady=5, fill='x', padx=10)
        
        # Admin button
        self.admin_btn = ModernButton(
            admin_frame,
            text="🔐 Admin Controls",
            command=self.show_admin_dialog,
            background=self.colors['warning'],
            foreground=self.colors['text']
        )
        self.admin_btn.pack(side='left', padx=5)
        
    def test_aws_connection(self):
        """Test AWS connectivity and required resources"""
        try:
            # Test Rekognition collection exists
            self.rekognition.describe_collection(CollectionId='facerecognition_collection')
            
            # Test DynamoDB table exists
            self.dynamodb.describe_table(TableName='facerecognition')
            
        except self.rekognition.exceptions.ResourceNotFoundException:
            raise Exception("Rekognition collection 'facerecognition_collection' not found")
        except self.dynamodb.exceptions.ResourceNotFoundException:
            raise Exception("DynamoDB table 'facerecognition' not found")
        except Exception as e:
            raise Exception(f"AWS connection test failed: {str(e)}")

    def toggle_camera(self):
        if not self.is_camera_on:
            try:
                # Initialize camera
                self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Try DirectShow backend
                if not self.cap.isOpened():
                    # Try default backend if DirectShow fails
                    self.cap = cv2.VideoCapture(0)
                    if not self.cap.isOpened():
                        raise Exception("Could not open camera!")
                
                # Test frame capture
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    raise Exception("Could not read from camera!")
                
                self.is_camera_on = True
                self.camera_btn.configure(
                    text="⏹ Stop Camera",
                    background=self.colors['danger']
                )
                self.capture_btn['state'] = 'normal'
                self.status_label.configure(text="Camera: ON")
                self.update_camera()
                
            except Exception as e:
                messagebox.showerror("Camera Error", str(e))
                self.stop_camera()
        else:
            self.stop_camera()
    
    def stop_camera(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.is_camera_on = False
        self.camera_btn.configure(
            text="▶ Start Camera",
            background=self.colors['primary']
        )
        self.capture_btn['state'] = 'disabled'
        self.status_label.configure(text="Camera: OFF")
        # Display camera icon
        self.camera_label.configure(image=self.camera_icon)
        self.camera_label.image = self.camera_icon  # Keep a reference
        
    def update_camera(self):
        if self.is_camera_on and self.cap is not None:
            try:
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    self.current_frame = frame
                    
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Convert to PIL Image
                    image = Image.fromarray(frame_rgb)
                    
                    # Resize frame while maintaining aspect ratio
                    width, height = image.size
                    max_size = 500
                    scale = min(max_size/width, max_size/height)
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    photo = ImageTk.PhotoImage(image)
                    self.camera_label.configure(image=photo)
                    self.camera_label.image = photo
                else:
                    raise Exception("Failed to capture frame")
                
                self.root.after(10, self.update_camera)
                
            except Exception as e:
                messagebox.showerror("Camera Error", f"Camera error: {str(e)}")
                self.stop_camera()
    
    def capture_and_recognize(self):
        if self.current_frame is None:
            messagebox.showerror("Error", "No frame captured!")
            return
            
        try:
            # Update capture time
            self.last_capture_time = datetime.now()
            self.time_label.configure(
                text=f"Last capture: {self.last_capture_time.strftime('%H:%M:%S')}"
            )
            
            # Convert frame to bytes
            frame_rgb = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG')
            image_bytes = img_byte_arr.getvalue()
            
            # Clear previous results
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, "🔍 Processing...\n\n")
            self.root.update()
            
            try:
                # Search faces in Rekognition
                response = self.rekognition.search_faces_by_image(
                    CollectionId='facerecognition_collection',
                    Image={'Bytes': image_bytes},
                    MaxFaces=5,
                    FaceMatchThreshold=80
                )
                
            except self.rekognition.exceptions.InvalidParameterException:
                self.results_text.delete(1.0, tk.END)
                self.results_text.insert(tk.END, "❌ No face detected in the image. Please try again.\n")
                return
            except Exception as e:
                self.results_text.delete(1.0, tk.END)
                self.results_text.insert(tk.END, f"❌ Recognition error: {str(e)}\n")
                return
            
            # Clear processing message
            self.results_text.delete(1.0, tk.END)
            
            # Process results
            if not response['FaceMatches']:
                self.results_text.insert(tk.END, "❌ No matching faces found.\n")
                return
                
            self.results_text.insert(tk.END, "✅ Matching Faces Found:\n")
            self.results_text.insert(tk.END, "=" * 40 + "\n\n")
            
            for match in response['FaceMatches']:
                face_id = match['Face']['FaceId']
                confidence = match['Face']['Confidence']
                
                try:
                    # Get person details from DynamoDB
                    face_data = self.dynamodb.get_item(
                        TableName='facerecognition',
                        Key={'RekognitionId': {'S': face_id}}
                    )
                    
                    if 'Item' in face_data:
                        name = face_data['Item']['FullName']['S']
                        self.results_text.insert(tk.END, f"👤 Name: {name}\n")
                        self.results_text.insert(tk.END, f"📊 Confidence: {confidence:.2f}%\n")
                        
                        # Mark attendance
                        if self.mark_attendance(name):
                            self.results_text.insert(tk.END, "✅ Attendance Marked\n")
                        else:
                            self.results_text.insert(tk.END, "ℹ️ Already marked present\n")
                        
                        self.results_text.insert(tk.END, "-" * 40 + "\n\n")
                    
                except Exception as e:
                    self.results_text.insert(tk.END, f"❌ Error fetching person details: {str(e)}\n")
                    continue
            
            # Show attendance summary
            self.show_attendance_summary()
                
        except Exception as e:
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, f"❌ Error: {str(e)}\n")
    
    def __del__(self):
        self.stop_camera()

    def update_results(self, message):
        """Helper method to update results text area"""
        if hasattr(self, 'results_text'):
            self.results_text.insert(tk.END, message + "\n")
            self.results_text.see(tk.END)  # Scroll to the end

    def create_camera_icon(self):
        """Create a camera icon for display when camera is off"""
        # Create a new image with a gray background
        icon_size = (500, 375)  # Standard webcam aspect ratio
        icon = Image.new('RGB', icon_size, '#E0E0E0')
        
        # Create camera icon shape
        draw = ImageDraw.Draw(icon)
        
        # Calculate camera dimensions
        cam_width = 200
        cam_height = 150
        x = (icon_size[0] - cam_width) // 2
        y = (icon_size[1] - cam_height) // 2
        
        # Draw camera body
        draw.rectangle([x, y, x + cam_width, y + cam_height], outline='#666666', width=3)
        
        # Draw camera lens
        lens_radius = 50
        lens_x = x + cam_width // 2
        lens_y = y + cam_height // 2
        draw.ellipse([lens_x - lens_radius, lens_y - lens_radius,
                     lens_x + lens_radius, lens_y + lens_radius],
                    outline='#666666', width=3)
        
        # Draw smaller circle inside lens
        inner_radius = 30
        draw.ellipse([lens_x - inner_radius, lens_y - inner_radius,
                     lens_x + inner_radius, lens_y + inner_radius],
                    outline='#666666', width=2)
        
        # Add text
        font_size = 20
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        text = "Camera Off"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (icon_size[0] - text_width) // 2
        text_y = y + cam_height + 20
        draw.text((text_x, text_y), text, fill='#666666', font=font)
        
        # Convert to PhotoImage
        self.camera_icon = ImageTk.PhotoImage(icon)

    def show_admin_dialog(self):
        """Show admin login dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Admin Authentication")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg'])
        
        # Center the dialog
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Main frame with padding
        main_frame = ttk.Frame(dialog, padding="20 20 20 20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="🔐 Admin Login",
            font=('Helvetica', 16, 'bold'),
            foreground=self.colors['text']
        )
        title_label.pack(pady=(0, 20))
        
        # Description
        desc_label = ttk.Label(
            main_frame,
            text="Please enter your credentials to access\nadministrative functions.",
            font=('Helvetica', 10),
            foreground=self.colors['text'],
            justify=tk.CENTER
        )
        desc_label.pack(pady=(0, 20))
        
        # Input frame
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Username
        username_frame = ttk.Frame(input_frame)
        username_frame.pack(fill=tk.X, pady=(0, 10))
        
        username_label = ttk.Label(
            username_frame,
            text="👤 Username:",
            font=('Helvetica', 10),
            foreground=self.colors['text']
        )
        username_label.pack(side=tk.LEFT, padx=(0, 10))
        
        username_entry = ttk.Entry(username_frame, width=25)
        username_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Password
        password_frame = ttk.Frame(input_frame)
        password_frame.pack(fill=tk.X)
        
        password_label = ttk.Label(
            password_frame,
            text="🔑 Password:",
            font=('Helvetica', 10),
            foreground=self.colors['text']
        )
        password_label.pack(side=tk.LEFT, padx=(0, 10))
        
        password_entry = ttk.Entry(password_frame, show="•", width=25)
        password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Error label (hidden initially)
        error_label = ttk.Label(
            main_frame,
            text="",
            font=('Helvetica', 10),
            foreground=self.colors['danger']
        )
        error_label.pack(pady=(0, 10))
        
        def verify_login():
            if (username_entry.get() == self.admin_username and 
                password_entry.get() == self.admin_password):
                dialog.destroy()
                self.show_attendance_clear_options()
            else:
                error_label.configure(text="❌ Invalid username or password")
                dialog.after(2000, lambda: error_label.configure(text=""))
                password_entry.delete(0, tk.END)
                password_entry.focus()
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Login button
        login_btn = ModernButton(
            button_frame,
            text="Login",
            command=verify_login,
            background=self.colors['primary'],
            foreground=self.colors['white']
        )
        login_btn.pack(side=tk.LEFT, padx=5, expand=True)
        
        # Cancel button
        cancel_btn = ModernButton(
            button_frame,
            text="Cancel",
            command=dialog.destroy,
            background=self.colors['danger'],
            foreground=self.colors['white']
        )
        cancel_btn.pack(side=tk.LEFT, padx=5, expand=True)
        
        # Bind Enter key to verify_login
        dialog.bind('<Return>', lambda e: verify_login())
        
        # Focus username entry
        username_entry.focus()

    def show_attendance_clear_options(self):
        """Show attendance clearing options dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Attendance Management")
        dialog.geometry("500x400")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg'])
        
        # Center the dialog
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Main frame with padding
        main_frame = ttk.Frame(dialog, padding="20 20 20 20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="📋 Attendance Management",
            font=('Helvetica', 16, 'bold'),
            foreground=self.colors['text']
        )
        title_label.pack(pady=(0, 20))
        
        # Options frame
        options_frame = ttk.Frame(main_frame)
        options_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        
        # Option 1: Clear Current Sheet
        option1_frame = ttk.Frame(options_frame)
        option1_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(
            option1_frame,
            text="Clear Current Sheet",
            font=('Helvetica', 12, 'bold'),
            foreground=self.colors['text']
        ).pack(anchor=tk.W)
        
        ttk.Label(
            option1_frame,
            text="Removes all attendance records for the selected date\nwhile keeping the file structure intact.",
            foreground=self.colors['text'],
            justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(5, 10))
        
        ModernButton(
            option1_frame,
            text="Clear Current Sheet",
            command=lambda: self.confirm_action(
                "Clear Current Sheet",
                "Are you sure you want to clear all records for the current date?",
                self.clear_current_attendance,
                dialog
            ),
            background=self.colors['warning'],
            foreground=self.colors['text']
        ).pack(anchor=tk.W)
        
        # Separator
        ttk.Separator(options_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=20)
        
        # Option 2: Create New Sheet
        option2_frame = ttk.Frame(options_frame)
        option2_frame.pack(fill=tk.X)
        
        ttk.Label(
            option2_frame,
            text="Create New Sheet",
            font=('Helvetica', 12, 'bold'),
            foreground=self.colors['text']
        ).pack(anchor=tk.W)
        
        ttk.Label(
            option2_frame,
            text="Archives all existing attendance records and starts fresh.\nOld records are safely stored in a timestamped archive folder.",
            foreground=self.colors['text'],
            justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(5, 10))
        
        ModernButton(
            option2_frame,
            text="Create New Sheet",
            command=lambda: self.confirm_action(
                "Create New Sheet",
                "Are you sure you want to archive current records and start fresh?",
                self.create_new_attendance_sheet,
                dialog
            ),
            background=self.colors['primary'],
            foreground=self.colors['white']
        ).pack(anchor=tk.W)
        
        # Close button at bottom
        ModernButton(
            main_frame,
            text="Close",
            command=dialog.destroy,
            background=self.colors['danger'],
            foreground=self.colors['white']
        ).pack(pady=(20, 0))

    def confirm_action(self, title, message, action, parent_dialog):
        """Show confirmation dialog before performing attendance management actions"""
        if messagebox.askyesno(title, message):
            if action():
                messagebox.showinfo("Success", f"{title} completed successfully!")
                parent_dialog.destroy()
            else:
                messagebox.showerror("Error", f"Failed to {title.lower()}")

    def clear_current_attendance(self):
        """Clear all values from current attendance sheet except headers"""
        try:
            if self.date_picker is None:
                selected_date = datetime.now()
            else:
                selected_date = self.date_picker.get_date()
            
            date_str = selected_date.strftime('%Y-%m-%d')
            attendance_file = os.path.join(self.attendance_dir, f"attendance_{date_str}.csv")
            
            if not os.path.exists(attendance_file):
                return False
            
            # Create new file with only headers
            with open(attendance_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Name', 'Date', 'Time'])
            
            self.update_results(f"Attendance sheet cleared for {date_str}")
            return True
            
        except Exception as e:
            self.update_results(f"Error clearing attendance: {str(e)}")
            return False

    def create_new_attendance_sheet(self):
        """Create a new attendance sheet with timestamp"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_dir = os.path.join(self.attendance_dir, f"archive_{timestamp}")
            os.makedirs(new_dir, exist_ok=True)
            
            # Move all existing attendance files to archive
            for file in os.listdir(self.attendance_dir):
                if file.startswith('attendance_') and file.endswith('.csv'):
                    old_path = os.path.join(self.attendance_dir, file)
                    new_path = os.path.join(new_dir, file)
                    os.rename(old_path, new_path)
            
            self.update_results(f"Previous attendance files archived to: archive_{timestamp}")
            
            # Initialize new attendance file
            self.init_attendance_file()
            return True
            
        except Exception as e:
            self.update_results(f"Error creating new attendance sheet: {str(e)}")
            return False

def main():
    root = tk.Tk()
    app = FaceRecognitionGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 