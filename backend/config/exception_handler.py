"""Project-wide DRF exception handler.

DRF's default handler only knows how to turn `APIException` subclasses into clean
JSON responses; anything else (a database `IntegrityError`, a Django model
`ValidationError`, a bare `ValueError`) bubbles up as an unhandled 500. Across an
API this large that means a single missing serializer check can leak a stack trace
and return 500 where the client deserves a 400.

This handler wraps the default one and maps the common "the request was bad"
exceptions to a 400 response with a consistent body shape:

    {"detail": "...", "code": "..."}

so the frontend can rely on every error being JSON, never an HTML 500 page.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, DataError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def custom_exception_handler(exc, context):
    # Let DRF handle everything it already understands (APIException, Http404,
    # PermissionDenied, etc.). If it returns a response, we're done.
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    # Translate a Django model-level ValidationError (e.g. from full_clean()) into
    # the same shape DRF uses for serializer validation errors.
    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
        return Response(detail, status=status.HTTP_400_BAD_REQUEST)

    # Database constraint violations (unique, not-null, FK) almost always mean the
    # client sent data that conflicts with existing rows — that's a 400, not a 500.
    if isinstance(exc, (IntegrityError, DataError)):
        return Response(
            {'detail': 'The request could not be completed because it conflicts with '
                       'existing data or violates a constraint.',
             'code': 'integrity_error'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Belt-and-braces for Http404 if it ever slips past DRF.
    if isinstance(exc, Http404):
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Anything else is a genuine server error — let it 500 so it's logged/alerted.
    return None
