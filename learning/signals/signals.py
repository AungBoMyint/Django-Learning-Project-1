from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse
from learning.signals import enrollment
import logging
from django_rest_passwordreset.signals import reset_password_token_created

logger = logging.getLogger(__name__)

@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    """
    Handles password reset tokens
    When a token is created, an e-mail needs to be sent to the user
    :param sender: View Class that sent the signal
    :param instance: View Instance that sent the signal
    :param reset_password_token: Token Model Object
    :param args:
    :param kwargs:
    :return:
    """
    # send an e-mail to the user
    try:
        context = {
        'current_user': reset_password_token.user,
        'username': reset_password_token.user.username,
        'email': reset_password_token.user.email,
        'reset_password_url': "{}?token={}".format(
            instance.request.build_absolute_uri(reverse('password_reset:reset-password-confirm')),
            reset_password_token.key)
        }

        # render email text
        email_html_message = render_to_string('email/password_reset_email.html', context)
        email_plaintext_message = render_to_string('email/password_reset_email.txt', context)

        msg = EmailMultiAlternatives(
            # title:
            "Password Reset for {title}".format(title="LearningApp"),
            # message:
            email_plaintext_message,
            # from:
            "noreply@yourdomain.com",
            # to:
            [reset_password_token.user.email]
        )
        msg.attach_alternative(email_html_message, "text/html")
        msg.send()
    except Exception as e:
        logger.error("Error sending email: %s", e)
                 

@receiver(enrollment)
def enrolled_email_to_admin(sender,**kwargs):
    student_email = kwargs["data"]["email"]
    # send an e-mail to the user
    context = {
        'student': kwargs["data"]["student"],
        'courses':kwargs["data"]["courses"],
        'enrollment_url': "http://127.0.0.1:8000/admin/learning/enrollment/",
    }

    # render email text
    email_html_message = render_to_string('email/enrolled_courses.html', context)
    email_plaintext_message = render_to_string('email/enrolled_courses.txt', context)

    msg = EmailMultiAlternatives(
        # title:
        "Student enrolled new courses",
        # message:
        email_plaintext_message,
        # from:
        student_email,
        # to:
        ["truelife787799@gmail.com"]
    )
    msg.attach_alternative(email_html_message, "text/html")
    msg.send()