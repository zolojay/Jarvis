#!/usr/bin/env python

import pandas as pd
import sqlite3
import os
from datetime import datetime

# Database path
DB_PATH = r"C:\Jarvis\Database\lemur_full_clone.db"

def insert_or_update_loadbench(load_id, testing_area, status, priority=None):
    """
    Insert or update a record in the LoadBench table.
    
    Parameters:
    load_id (int): The reactor load ID
    testing_area (str): The testing area
    status (str): The status of the load
    priority (int, optional): The priority value. If None, will auto-assign based on status.
    
    Returns:
    bool: True if successful, False otherwise
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if the load already exists in LoadBench
        cursor.execute("SELECT id, status, priority, testing_area FROM LoadBench WHERE load_id = ?", (load_id,))
        existing = cursor.fetchone()
        
        # Auto-determine priority if not provided
        if priority is None:
            if status.upper() == 'BACKLOG':
                # If transitioning to Backlog or new Backlog assignment, assign next priority
                cursor.execute(
                    "SELECT MAX(priority) FROM LoadBench WHERE testing_area = ? AND UPPER(status) = 'BACKLOG'",
                    (testing_area,)
                )
                max_priority = cursor.fetchone()[0]
                priority = (max_priority + 1) if max_priority is not None else 100
            else:
                # For non-backlog status, use default priority or existing
                priority = 100 if not existing else existing[2]
        
        if existing:
            # Update existing record
            cursor.execute(
                "UPDATE LoadBench SET testing_area = ?, status = ?, priority = ?, assigned_date = DATE('now') WHERE load_id = ?",
                (testing_area, status, priority, load_id)
            )
        else:
            # Insert new record
            cursor.execute(
                "INSERT INTO LoadBench (load_id, testing_area, status, priority, assigned_date) VALUES (?, ?, ?, ?, DATE('now'))",
                (load_id, testing_area, status, priority)
            )
        
        conn.commit()
        return True
    
    except Exception as e:
        conn.rollback()
        print(f"Error for load {load_id}: {str(e)}")
        return False
    
    finally:
        conn.close()

def bulk_update_loadbench():
    """
    Bulk update the LoadBench table with the provided data.
    """
    print("Starting bulk update process...")
    
    # Define the data from the provided table
    data = [
        {'load_id': 296, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 297, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 458, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 294, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 295, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 298, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 299, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 300, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 228, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 250, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 251, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 252, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 253, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 255, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 256, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 257, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 258, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 259, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 260, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 261, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 262, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 263, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 264, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 265, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 266, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 267, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 271, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 272, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 273, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 274, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 275, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 276, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 277, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 279, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 280, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 281, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 282, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 283, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 284, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 285, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 286, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 287, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 288, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 289, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 290, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 291, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 292, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 293, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 301, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 302, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 303, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 304, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 313, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 314, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 316, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 317, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 318, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 319, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 320, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 321, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 322, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 323, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 324, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 325, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 326, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 333, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 355, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 356, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 468, 'status': 'Test Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 334, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 335, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 327, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 469, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 328, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 330, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 331, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 378, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 379, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 380, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 397, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 332, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 373, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 337, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 466, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 361, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 371, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 418, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 396, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 426, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 370, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 368, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 369, 'status': 'Test Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 583, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 451, 'status': 'Report Delivered', 'testing_area': 'Quarter Bench'},
        {'load_id': 372, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 429, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 598, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 377, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 585, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 502, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 503, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 374, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 476, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 473, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 394, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 393, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 392, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 428, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 427, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 420, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 603, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 443, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 442, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 441, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 472, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 586, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 395, 'status': 'Test Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 637, 'status': 'Test Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 528, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 529, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 457, 'status': 'Test Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 456, 'status': 'Test Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 507, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 431, 'status': 'Test Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 508, 'status': 'Test Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 430, 'status': 'QC Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 460, 'status': 'Test Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 516, 'status': 'Test Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 515, 'status': 'Test Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 470, 'status': 'Test Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 524, 'status': 'Test Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 584, 'status': 'Test Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 498, 'status': 'Test Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 582, 'status': 'Test Complete', 'testing_area': 'Quarter Bench'},
        {'load_id': 499, 'status': 'In Reactor', 'testing_area': 'Quarter Bench'},
        {'load_id': 540, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 435, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 488, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 487, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 579, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 580, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 581, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 481, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 482, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 610, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 609, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 474, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 523, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 615, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 614, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 613, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 660, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 659, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 658, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 471, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 657, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 477, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 478, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 479, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 480, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 483, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 484, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 485, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 490, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 491, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 492, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 493, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 495, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 496, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 497, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 500, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 501, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 504, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 505, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 506, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 509, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 510, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 511, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 512, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 513, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 514, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 530, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 531, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 532, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 533, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 534, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 535, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 536, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 537, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 538, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 539, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 541, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 542, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 543, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 544, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 545, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 546, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 547, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 548, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 607, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 608, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 616, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 617, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 618, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 619, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 620, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 621, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 622, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 623, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 624, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 625, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 626, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 627, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 628, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 629, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 630, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 636, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 638, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 654, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 653, 'status': 'Backlog', 'testing_area': 'Quarter Bench'},
        {'load_id': 551, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 351, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 352, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 347, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 348, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 349, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 350, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 381, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 382, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 383, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 384, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 411, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 408, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 336, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 358, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 357, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 353, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 354, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 587, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 364, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 365, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 366, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 360, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 550, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 359, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 339, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 340, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 342, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 341, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 416, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 414, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 415, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 343, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 344, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 375, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 376, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 367, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 345, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 362, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 346, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 385, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 386, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 419, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 387, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 388, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 556, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 558, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 553, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 403, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 559, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 405, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 404, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 406, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 407, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 560, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 563, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 398, 'status': 'QC Complete', 'testing_area': 'Full Bench'},
        {'load_id': 399, 'status': 'QC Complete', 'testing_area': 'Full Bench'},
        {'load_id': 436, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 400, 'status': 'QC Complete', 'testing_area': 'Full Bench'},
        {'load_id': 401, 'status': 'QC Complete', 'testing_area': 'Full Bench'},
        {'load_id': 437, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 438, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 402, 'status': 'QC Complete', 'testing_area': 'Full Bench'},
        {'load_id': 422, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 423, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 517, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 518, 'status': 'QC Complete', 'testing_area': 'Full Bench'},
        {'load_id': 439, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 424, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 425, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 566, 'status': 'QC Complete', 'testing_area': 'Full Bench'},
        {'load_id': 467, 'status': 'Test Complete', 'testing_area': 'Full Bench'},
        {'load_id': 527, 'status': 'Test Complete', 'testing_area': 'Full Bench'},
        {'load_id': 519, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 521, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 520, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 522, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 444, 'status': 'Test Complete', 'testing_area': 'Full Bench'},
        {'load_id': 363, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 445, 'status': 'Test Complete', 'testing_area': 'Full Bench'},
        {'load_id': 409, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 526, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 489, 'status': 'Report Delivered', 'testing_area': 'Full Bench'},
        {'load_id': 446, 'status': 'Test Complete', 'testing_area': 'Full Bench'},
        {'load_id': 448, 'status': 'Test Complete', 'testing_area': 'Full Bench'},
        {'load_id': 449, 'status': 'Test Complete', 'testing_area': 'Full Bench'},
        {'load_id': 450, 'status': 'Test Complete', 'testing_area': 'Full Bench'},
        {'load_id': 421, 'status': 'Test Complete', 'testing_area': 'Full Bench'},
        {'load_id': 464, 'status': 'Test Complete', 'testing_area': 'Full Bench'},
        {'load_id': 465, 'status': 'Test Complete', 'testing_area': 'Full Bench'},
        {'load_id': 461, 'status': 'Test Complete', 'testing_area': 'Full Bench'},
        {'load_id': 462, 'status': 'Test Complete', 'testing_area': 'Full Bench'},
        {'load_id': 463, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 601, 'status': 'In Reactor', 'testing_area': 'Full Bench'},
        {'load_id': 602, 'status': 'In Reactor', 'testing_area': 'Full Bench'},
        {'load_id': 567, 'status': 'In Reactor', 'testing_area': 'Full Bench'},
        {'load_id': 595, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 594, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 593, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 592, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 591, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 590, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 589, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 588, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 486, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 604, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 561, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 562, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 564, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 565, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 557, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 555, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 568, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 569, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 570, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 571, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 572, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 573, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 574, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 575, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 576, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 577, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 578, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 410, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 447, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 459, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 596, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 597, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 600, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 605, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 606, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 611, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 612, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 631, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 632, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 633, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 634, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 635, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 639, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 640, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 641, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 329, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 413, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 549, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 552, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 656, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 655, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 643, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 642, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 647, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 646, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 645, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 644, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 652, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 651, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 650, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 649, 'status': 'Backlog', 'testing_area': 'Full Bench'},
        {'load_id': 648, 'status': 'Backlog', 'testing_area': 'Full Bench'}
    ]
    
    # Count variables to track progress
    total_loads = len(data)
    processed_loads = 0
    success_count = 0
    error_count = 0
    
    print(f"Found {total_loads} loads to process")
    
    # Process each load
    for load in data:
        try:
            # Get the load data
            load_id = load['load_id']
            testing_area = load['testing_area']
            status = load['status']
            
            # Insert or update the load in the database
            result = insert_or_update_loadbench(
                load_id=load_id,
                testing_area=testing_area,
                status=status,
                priority=None  # Let priority auto-determine
            )
            
            # Update counts
            processed_loads += 1
            if result:
                success_count += 1
            else:
                error_count += 1
            
            # Print progress every 20 loads
            if processed_loads % 20 == 0:
                print(f"Processed {processed_loads}/{total_loads} loads ({processed_loads/total_loads*100:.1f}%)")
                
        except Exception as e:
            error_count += 1
            processed_loads += 1
            print(f"Error processing load {load.get('load_id', 'unknown')}: {str(e)}")
    
    # Print summary
    print("\nBulk update completed!")
    print(f"Total loads processed: {processed_loads}")
    print(f"Successful updates: {success_count}")
    print(f"Errors: {error_count}")
    
    return success_count, error_count

# Alternative implementation using CSV for future use
def bulk_update_from_csv(csv_path):
    """
    Alternative implementation that loads data from a CSV file
    
    Parameters:
    csv_path (str): Path to CSV file with load_id, status, testing_area columns
    """
    print(f"Loading data from {csv_path}...")
    
    try:
        # Load the CSV file
        df = pd.read_csv(csv_path)
        
        # Verify required columns exist
        required_cols = ['load_id', 'status', 'testing_area']
        for col in required_cols:
            if col not in df.columns:
                print(f"Error: CSV file is missing required column '{col}'")
                return 0, 0
        
        print(f"Found {len(df)} loads in CSV file")
        
        # Process each load
        success_count = 0
        error_count = 0
        
        for idx, row in df.iterrows():
            try:
                # Insert or update the load
                result = insert_or_update_loadbench(
                    load_id=int(row['load_id']),
                    testing_area=row['testing_area'],
                    status=row['status'],
                    priority=None  # Let priority auto-determine
                )
                
                if result:
                    success_count += 1
                else:
                    error_count += 1
                    
                # Print progress every 20 loads
                if (idx + 1) % 20 == 0:
                    print(f"Processed {idx + 1}/{len(df)} loads ({(idx + 1)/len(df)*100:.1f}%)")
                    
            except Exception as e:
                error_count += 1
                print(f"Error processing load {row.get('load_id', 'unknown')}: {str(e)}")
        
        # Print summary
        print("\nBulk update completed!")
        print(f"Total loads processed: {len(df)}")
        print(f"Successful updates: {success_count}")
        print(f"Errors: {error_count}")
        
        return success_count, error_count
        
    except Exception as e:
        print(f"Error reading CSV file: {str(e)}")
        return 0, 0

# Export current LoadBench to CSV (useful before making changes)
def export_loadbench_to_csv(output_path=None):
    """
    Export the LoadBench table to a CSV file
    
    Parameters:
    output_path (str): Path to save the CSV file (default: creates timestamped file)
    
    Returns:
    str: Path to the saved CSV file
    """
    if output_path is None:
        # Use the script directory with timestamp
        script_dir = os.path.dirname(os.path.abspath(__file__))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(script_dir, f"loadbench_export_{timestamp}.csv")
    
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        
        # Query the LoadBench table
        query = """
        SELECT 
            lb.load_id, lb.testing_area, lb.status, lb.priority, lb.assigned_date,
            lr.number as lab_request_number, lr.job_number, lr.pcn
        FROM 
            LoadBench lb
        LEFT JOIN
            ReactorLoads rl ON lb.load_id = rl.id
        LEFT JOIN
            LabRequests lr ON rl.lab_request_id = lr.id
        """
        
        # Load into a dataframe
        df = pd.read_sql_query(query, conn)
        y
        # Save to CSV
        df.to_csv(output_path, index=False)
        
        print(f"Successfully exported LoadBench table to {output_path}")
        print(f"Exported {len(df)} records")
        
        conn.close()
        return output_path
        
    except Exception as e:
        print(f"Error exporting LoadBench table: {str(e)}")
        return None

# Main function
def main():
    print("Lab Load Scheduler - Bulk Update Utility")
    print("========================================")
    
    # Create a backup first by exporting to CSV
    print("\nCreating backup of current LoadBench table...")
    backup_path = export_loadbench_to_csv()
    
    if backup_path:
        print("\nNOTE: A backup of the current state has been created at:")
        print(f"      {backup_path}")
        print("      Keep this file in case you need to restore the previous state.\n")
    
    # Ask for confirmation
    confirmation = input("Are you sure you want to proceed with the bulk update? (y/n): ")
    
    if confirmation.lower() not in ['y', 'yes']:
        print("Operation cancelled.")
        return
    
    # Perform the bulk update
    print("\nStarting bulk update...")
    success_count, error_count = bulk_update_loadbench()
    
    # Final status message
    if error_count == 0:
        print("\nBulk update completed successfully!")
    else:
        print(f"\nBulk update completed with {error_count} errors.")
        print("Please check the log messages above for details.")

# Execute the script
if __name__ == "__main__":
    main()