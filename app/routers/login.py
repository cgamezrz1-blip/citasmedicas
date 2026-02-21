from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import autenticar_usuario, crear_access_token
from app.database import get_db
from app.schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Autentica un usuario y retorna un JWT token.
    """
    usuario = autenticar_usuario(db, request.email, request.password)

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = crear_access_token(data={"sub": usuario.email, "id": usuario.id})

    return TokenResponse(access_token=token)
