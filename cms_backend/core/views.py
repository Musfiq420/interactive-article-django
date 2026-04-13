from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class LogoutView(APIView):
    """
    API View to handle user logout.
    Deletes the authentication token associated with the user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Delete the user's token to log them out
            request.user.auth_token.delete()
        except (AttributeError, Token.DoesNotExist):
            # Handle case where token doesn't exist gracefully
            pass
        
        return Response(
            {"detail": "Successfully logged out."}, 
            status=status.HTTP_200_OK
        )