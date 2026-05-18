from enum import Enum


class LoginMethod(str, Enum):
    ACCOUNT_ID = "account_id"
    USERNAME = "username"


class PostCategory(str, Enum):
    CAMPUS_LANDMARK = "Campus Landmark"
    STUDY_SPACE = "Study Space"
    STUDENT_LIFE = "Student Life"
    FOOD_AND_CAFE = "Food and Cafe"
    SPORTS_AND_LEISURE = "Sports and Leisure"
    DIGITAL_MEMORY = "Digital Memory"


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"

