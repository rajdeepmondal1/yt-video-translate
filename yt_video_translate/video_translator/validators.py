# from django.core.exceptions import ValidationError
# from django.core.validators import RegexValidator
# from django.utils.translation import gettext_lazy as _


# def validate_youtube_url(value):
#     valid_regex = RegexValidator(
#         r"^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$",
#         "Enter a valid Youtube Link.",
#     )
#     if value % 2 != 0:
#         raise ValidationError(
#             _("%(value)s is not an even number"),
#             params={"value": value},
#         )
