import os
import json
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Union
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
from google.genai import types

from src.config import settings
from src.models.activity import ConnectedAccount
from src.models.plan import TrainingSession, TrainingPlan
from src.services.planner_service import get_gemini_client

# Garmin Connect client imports
from garminconnect import Garmin
from garminconnect.workout import (
    RunningWorkout,
    WorkoutSegment,
    ExecutableStep,
    RepeatGroup,
    StepType,
    ConditionType,
    TargetType
)
from pydantic import BaseModel, Field

# -------------------------------------------------------------
# Password Encryption Helpers
# -------------------------------------------------------------

def encrypt_password(password: str) -> str:
    """Encrypt a raw string using Fernet symmetric encryption."""
    f = Fernet(settings.GARMIN_ENCRYPTION_KEY.encode())
    return f.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str) -> str:
    """Decrypt an encrypted string using Fernet symmetric encryption."""
    f = Fernet(settings.GARMIN_ENCRYPTION_KEY.encode())
    return f.decrypt(encrypted_password.encode()).decode()

# -------------------------------------------------------------
# Connection Verification
# -------------------------------------------------------------

def test_garmin_login(email: str, password: str) -> bool:
    """Validate Garmin login credentials by attempting to authenticate."""
    try:
        client = Garmin(email, password)
        client.login()
        return True
    except Exception as e:
        raise Exception(f"Garmin Connection Error: {str(e)}")

# -------------------------------------------------------------
# Gemini Structured Workout Parser Schema
# -------------------------------------------------------------

class GeminiSubStep(BaseModel):
    step_type: str = Field(default="interval", description="Step type: warmup, cooldown, interval, recovery, rest, other")
    end_condition: str = Field(default="time", description="End condition trigger: time, distance, lap_button")
    end_condition_value: float = Field(default=0.0, description="Duration value: seconds if time, miles if distance, 0.0 if lap_button")
    target_type: str = Field(default="no_target", description="Target type: no_target, pace, heart_rate")
    target_value_low: float = Field(default=0.0, description="Slower velocity in m/s if pace, min HR in BPM if heart_rate, 0.0 otherwise")
    target_value_high: float = Field(default=0.0, description="Faster velocity in m/s if pace, max HR in BPM if heart_rate, 0.0 otherwise")
    description: str = Field(default="", description="Short instruction summary for the step")

class GeminiWorkoutStep(BaseModel):
    is_repeat_group: bool = Field(description="True if this represents a repeat block containing sub-steps, False if a single step.")
    repeat_iterations: int = Field(default=1, description="Number of iterations if is_repeat_group is True.")
    repeat_steps: Optional[List[GeminiSubStep]] = Field(default=None, description="Sub-steps to repeat if is_repeat_group is True.")

    # Fields for normal individual step
    step_type: str = Field(default="interval", description="Step type: warmup, cooldown, interval, recovery, rest, other")
    end_condition: str = Field(default="time", description="End condition trigger: time, distance, lap_button")
    end_condition_value: float = Field(default=0.0, description="Duration value: seconds if time, miles if distance, 0.0 if lap_button")
    target_type: str = Field(default="no_target", description="Target type: no_target, pace, heart_rate")
    target_value_low: float = Field(default=0.0, description="Slower velocity in m/s if pace, min HR in BPM if heart_rate, 0.0 otherwise")
    target_value_high: float = Field(default=0.0, description="Faster velocity in m/s if pace, max HR in BPM if heart_rate, 0.0 otherwise")
    description: str = Field(default="", description="Short instruction summary for the step")

class GeminiGarminWorkout(BaseModel):
    session_id: str = Field(description="The unique database ID of the session")
    workoutName: str = Field(description="A clean, concise name for the watch workout (max 15 characters, letters/numbers only)")
    description: str = Field(description="A brief description of the workout")
    estimatedDurationInSecs: int = Field(description="Total estimated workout duration in seconds")
    steps: List[GeminiWorkoutStep] = Field(description="Ordered list of steps or repeat groups")

class GeminiGarminWorkoutResponse(BaseModel):
    workouts: List[GeminiGarminWorkout] = Field(description="A list of structured workouts")

# -------------------------------------------------------------
# Garmin JSON Mapper
# -------------------------------------------------------------

def map_gemini_step_to_garmin(step: GeminiWorkoutStep, step_order: int) -> Union[ExecutableStep, RepeatGroup]:
    """Map the simplified Gemini step/repeat schema to garminconnect Pydantic models."""
    if step.is_repeat_group:
        sub_steps = []
        for idx, sub in enumerate(step.repeat_steps or []):
            sub_mapped = _map_individual_step(sub, step_order=idx + 1)
            sub_steps.append(sub_mapped)
        
        return RepeatGroup(
            stepOrder=step_order,
            numberOfIterations=step.repeat_iterations,
            workoutSteps=sub_steps,
            stepType={
                "stepTypeId": StepType.REPEAT,
                "stepTypeKey": "repeat",
                "displayOrder": 6
            }
        )
    else:
        return _map_individual_step(step, step_order)

def _map_individual_step(step: Union[GeminiWorkoutStep, GeminiSubStep], step_order: int) -> ExecutableStep:
    """Helper to map a single step's fields to a Garmin ExecutableStep."""
    # Map step type
    st_map = {
        "warmup": (StepType.WARMUP, "warmup", 1),
        "cooldown": (StepType.COOLDOWN, "cooldown", 2),
        "interval": (StepType.INTERVAL, "interval", 3),
        "recovery": (StepType.RECOVERY, "recovery", 4),
        "rest": (StepType.REST, "rest", 5),
        "other": (StepType.OTHER, "other", 7)
    }
    st_id, st_key, st_order = st_map.get(step.step_type.lower(), (StepType.INTERVAL, "interval", 3))
    
    # Map end condition
    ec_map = {
        "lap_button": (ConditionType.LAP_BUTTON, "lap.button", 1),
        "time": (ConditionType.TIME, "time", 2),
        "distance": (ConditionType.DISTANCE, "distance", 3)
    }
    ec_id, ec_key, ec_order = ec_map.get(step.end_condition.lower(), (ConditionType.TIME, "time", 2))
    
    # Calculate condition value
    ec_val = step.end_condition_value
    if step.end_condition.lower() == "distance":
        ec_val = round(step.end_condition_value * 1609.34, 2)  # Miles to meters
    elif step.end_condition.lower() == "lap_button":
        ec_val = 0.0
        
    # Map target type
    tt_map = {
        "no_target": (TargetType.NO_TARGET, "no.target", 1),
        "pace": (TargetType.SPEED_ZONE, "speed.zone", 5), # Absolute pace/speed targets
        "heart_rate": (TargetType.HEART_RATE_ZONE, "heart.rate.zone", 4)
    }
    tt_id, tt_key, tt_order = tt_map.get(step.target_type.lower(), (TargetType.NO_TARGET, "no.target", 1))
    
    # Initialize ExecutableStep
    exec_step = ExecutableStep(
        stepOrder=step_order,
        stepType={
            "stepTypeId": st_id,
            "stepTypeKey": st_key,
            "displayOrder": st_order
        },
        endCondition={
            "conditionTypeId": ec_id,
            "conditionTypeKey": ec_key,
            "displayOrder": ec_order,
            "displayable": True
        },
        endConditionValue=ec_val,
        targetType={
            "workoutTargetTypeId": tt_id,
            "workoutTargetTypeKey": tt_key,
            "displayOrder": tt_order
        }
    )
    
    # Add target ranges if configured
    if step.target_type.lower() == "pace" and step.target_value_high > 0:
        # Set absolute speed targets in meters per second
        exec_step.targetValueLow = step.target_value_low   # Slower velocity
        exec_step.targetValueHigh = step.target_value_high # Faster velocity
    elif step.target_type.lower() == "heart_rate" and step.target_value_high > 0:
        # Set heart rate targets in BPM
        exec_step.targetValueLow = step.target_value_low
        exec_step.targetValueHigh = step.target_value_high
        
    return exec_step

# -------------------------------------------------------------
# Plan Synchronization Service
# -------------------------------------------------------------

def push_plan_to_garmin(user_id: str, db: Session) -> Dict[str, Any]:
    """Fetch user's upcoming active plan sessions, parse them with Gemini, and push to GarminConnect calendar."""
    # Retrieve credentials
    account = db.query(ConnectedAccount).filter(
        ConnectedAccount.user_id == user_id,
        ConnectedAccount.provider == "garmin"
    ).first()
    
    if not account:
        raise Exception("Garmin account credentials are not configured. Please set them up in profile settings first.")
        
    garmin_email = account.access_token
    garmin_password = decrypt_password(account.refresh_token)
    
    # Fetch active plan and its future sessions
    active_plan = db.query(TrainingPlan).filter(
        TrainingPlan.user_id == user_id,
        TrainingPlan.status == "active"
    ).first()
    
    if not active_plan:
        raise Exception("No active training plan found. Please generate a training plan first.")
        
    today = date.today()
    future_sessions = db.query(TrainingSession).filter(
        TrainingSession.plan_id == active_plan.id,
        TrainingSession.date >= today,
        TrainingSession.type != "Rest"  # Skip Rest Days
    ).order_by(TrainingSession.date).all()
    
    if not future_sessions:
        return {
            "status": "success",
            "message": "No upcoming training sessions to sync (rest days or completed plans skipped)."
        }
        
    # Generate structured workout list using Gemini in a single batch call
    session_list_text = []
    for s in future_sessions:
        session_list_text.append({
            "id": s.id,
            "date": s.date.isoformat(),
            "type": s.type,
            "name": s.name,
            "description": s.description,
            "duration_minutes": s.duration_minutes,
            "distance_miles": s.distance_miles,
            "target_pace_range": s.target_pace_range,
            "target_hr_zone": s.target_hr_zone,
            "target_rpe": s.target_rpe
        })
        
    prompt = (
        "You are an expert running coach parsing calendar training runs into Garmin watch structured workouts.\n\n"
        "Input Sessions:\n"
        f"{json.dumps(session_list_text, indent=2)}\n\n"
        "For each input session:\n"
        "1. Create a structured workout containing steps: warmup, interval, recovery, cooldown.\n"
        "2. Parse intervals/repeats if the session text describes them (e.g., '4x 800m with 2 min recovery' becomes a repeat group with 4 iterations, containing a distance-based run step of 800m (0.50 miles) and a time-based recovery step of 120 seconds).\n"
        "3. Set end conditions correctly: time (value in seconds) or distance (value in miles) or lap_button (value 0.0).\n"
        "   - Default warmup and cooldown to lap_button (value 0.0) so the runner can start/stop them manually, or time/distance if specified.\n"
        "4. Calculate target values for speed (meters per second) if the target_type is 'pace':\n"
        "   - Formula: speed (m/s) = 1609.34 / (pace in seconds per mile).\n"
        "   - Slower pace velocity goes to target_value_low. Faster pace velocity goes to target_value_high.\n"
        "   - Example: Pace 7:30 to 8:00 per mile:\n"
        "     - 8:00 pace = 480 sec/mi -> Speed = 1609.34 / 480 = 3.35 m/s (slower speed, maps to target_value_low).\n"
        "     - 7:30 pace = 450 sec/mi -> Speed = 1609.34 / 450 = 3.58 m/s (faster speed, maps to target_value_high).\n"
        "5. Calculate target values for heart rate (BPM) if target_type is 'heart_rate' (e.g., 140 to 155 BPM -> low=140.0, high=155.0).\n"
        "6. Ensure the estimatedDurationInSecs is the sum of all steps' durations (for lap_button steps, assume a reasonable estimate like 600 seconds for warmups/cooldowns).\n"
    )
    
    try:
        client = get_gemini_client()
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GeminiGarminWorkoutResponse
            )
        )
        parsed_response = GeminiGarminWorkoutResponse.model_validate_json(response.text)
    except Exception as gemini_err:
        raise Exception(f"Failed to generate structured watch workouts using AI: {str(gemini_err)}")
        
    # Connect to Garmin
    try:
        garmin_client = Garmin(garmin_email, garmin_password)
        garmin_client.login()
    except Exception as login_err:
        raise Exception(f"Failed to log in to Garmin Connect. Please verify your credentials: {str(login_err)}")
        
    # Clear existing scheduled workouts on the dates we are about to push to prevent duplicates
    target_dates = {s.date.isoformat() for s in future_sessions}
    months_to_fetch = {(s.date.year, s.date.month) for s in future_sessions}
    
    for y, m in months_to_fetch:
        try:
            scheduled = garmin_client.get_scheduled_workouts(y, m)
            if scheduled and isinstance(scheduled, list):
                for item in scheduled:
                    cal_date = item.get("calendarDate")
                    schedule_id = item.get("workoutScheduleId")
                    if cal_date in target_dates and schedule_id:
                        garmin_client.unschedule_workout(schedule_id)
        except Exception as fetch_err:
            import logging
            logging.getLogger(__name__).warning(f"Failed to clear existing calendar workouts for {y}-{m}: {fetch_err}")
            
    synced_count = 0
    # Process and upload each structured workout
    for workout in parsed_response.workouts:
        # Find corresponding session from database to get date
        db_session = next((s for s in future_sessions if s.id == workout.session_id), None)
        if not db_session:
            continue
            
        # Map steps to GarminConnect schema
        workout_steps = []
        for index, step in enumerate(workout.steps):
            workout_steps.append(map_gemini_step_to_garmin(step, step_order=index + 1))
            
        # Create workout segment
        segment = WorkoutSegment(
            segmentOrder=1,
            sportType={"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1},
            workoutSteps=workout_steps
        )
        
        # Build Garmin running workout model
        running_workout = RunningWorkout(
            workoutName=workout.workoutName,
            description=workout.description,
            estimatedDurationInSecs=workout.estimatedDurationInSecs,
            workoutSegments=[segment]
        )
        
        # Convert to dictionary/JSON
        workout_json = running_workout.model_dump()
        
        try:
            # Upload workout
            res = garmin_client.upload_workout(workout_json)
            workout_id = res["workoutId"]
            
            # Schedule workout on calendar
            date_str = db_session.date.isoformat()
            garmin_client.schedule_workout(workout_id, date_str)
            synced_count += 1
        except Exception as upload_err:
            # Continue trying others even if one fails
            import logging
            logging.getLogger(__name__).error(f"Error syncing session {workout.workoutName} on {db_session.date}: {upload_err}")
            
    return {
        "status": "success",
        "message": f"Successfully pushed {synced_count} structured running workouts to your Garmin calendar!",
        "synced_count": synced_count
    }
