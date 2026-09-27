from src.app.exceptions import ConflictException, ForbiddenException, UnauthorizedException


class IncorrectLoginDataException(UnauthorizedException):
    def __init__(self):
        super().__init__("Incorrect login data.")


class UserIsBannedException(ConflictException):
    def __init__(self):
        super().__init__("User is banned.")


class CurrentUserIsBannedException(ForbiddenException):
    def __init__(self):
        super().__init__("User is banned.")


class CannotBanAdminException(ForbiddenException):
    def __init__(self):
        super().__init__("You cannot ban user with administrator right.")


class CannotBanYourselfException(ConflictException):
    def __init__(self):
        super().__init__("You cannot ban yourself.")


class CannotUnbanYourselfException(ForbiddenException):
    def __init__(self):
        super().__init__("You cannot unban yourself.")
