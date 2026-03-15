#!/usr/bin/env python3
"""
Query and display GuardianView incidents from Firebase Firestore.

Usage:
    python scripts/view_firebase_incidents.py
    python scripts/view_firebase_incidents.py --session gv-session-abc123
    python scripts/view_firebase_incidents.py --severity critical
"""

import os
import sys
from datetime import datetime
import argparse

# Add parent directory to path to import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'app', '.env'))


def initialize_firebase():
    """Initialize Firebase Admin SDK."""
    try:
        firebase_admin.get_app()
        print("✅ Firebase already initialized")
    except ValueError:
        firebase_creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
        if not firebase_creds_path:
            print("❌ FIREBASE_CREDENTIALS_PATH not set in .env")
            sys.exit(1)

        # Handle relative paths
        if firebase_creds_path.startswith("./"):
            firebase_creds_path = os.path.join(
                os.path.dirname(__file__), '..', 'app', firebase_creds_path[2:]
            )

        if not os.path.exists(firebase_creds_path):
            print(f"❌ Firebase credentials not found at: {firebase_creds_path}")
            sys.exit(1)

        cred = credentials.Certificate(firebase_creds_path)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized")

    return firestore.client()


def format_timestamp(ts_str):
    """Format ISO timestamp to readable format."""
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return ts_str


def view_all_incidents(db, session_id=None, severity=None, limit=50):
    """View all incidents from Firebase."""
    print("\n" + "="*80)
    print("GUARDIANVIEW INCIDENTS")
    print("="*80 + "\n")

    # Build query
    query = db.collection('incidents')

    if session_id:
        query = query.where('session_id', '==', session_id)
        print(f"📊 Filtering by session: {session_id}\n")

    if severity:
        query = query.where('severity', '==', severity.lower())
        print(f"⚠️  Filtering by severity: {severity.upper()}\n")

    query = query.order_by('timestamp', direction=firestore.Query.DESCENDING)
    query = query.limit(limit)

    # Execute query
    incidents = query.stream()

    count = 0
    for doc in incidents:
        count += 1
        data = doc.to_dict()

        severity_icon = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢'
        }.get(data.get('severity', 'low').lower(), '⚪')

        print(f"{severity_icon} [{data.get('severity', 'UNKNOWN').upper()}] {format_timestamp(data.get('timestamp', 'N/A'))}")
        print(f"   Session: {data.get('session_id', 'N/A')}")
        print(f"   Description: {data.get('description', 'N/A')}")
        if data.get('regulation'):
            print(f"   Regulation: {data.get('regulation')}")
        if data.get('recommendation'):
            print(f"   Recommendation: {data.get('recommendation')}")
        print(f"   Document ID: {doc.id}")
        print()

    if count == 0:
        print("No incidents found.")
    else:
        print(f"Total incidents shown: {count}")
        if count == limit:
            print(f"(Limited to {limit} results)")

    print("\n" + "="*80 + "\n")


def view_session_summary(db):
    """View session summaries."""
    print("\n" + "="*80)
    print("SESSION SUMMARIES")
    print("="*80 + "\n")

    sessions = db.collection('sessions').stream()

    count = 0
    for doc in sessions:
        count += 1
        data = doc.to_dict()

        print(f"📋 Session: {doc.id}")
        print(f"   Incident Count: {data.get('incident_count', 0)}")
        print(f"   Last Incident: {data.get('last_incident', 'N/A')}")

        if data.get('last_updated'):
            # Handle Firestore timestamp
            last_updated = data['last_updated']
            if hasattr(last_updated, 'timestamp'):
                dt = datetime.fromtimestamp(last_updated.timestamp())
                print(f"   Last Updated: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

    if count == 0:
        print("No sessions found.")
    else:
        print(f"Total sessions: {count}")

    print("\n" + "="*80 + "\n")


def main():
    parser = argparse.ArgumentParser(description='View GuardianView incidents from Firebase')
    parser.add_argument('--session', help='Filter by session ID')
    parser.add_argument('--severity', choices=['critical', 'high', 'medium', 'low'],
                       help='Filter by severity level')
    parser.add_argument('--limit', type=int, default=50, help='Maximum number of incidents to show')
    parser.add_argument('--sessions', action='store_true', help='Show session summaries')

    args = parser.parse_args()

    # Initialize Firebase
    db = initialize_firebase()

    # Show data
    if args.sessions:
        view_session_summary(db)
    else:
        view_all_incidents(db, session_id=args.session, severity=args.severity, limit=args.limit)


if __name__ == '__main__':
    main()
