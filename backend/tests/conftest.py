import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app import app
from src.database import Base, get_db
from src.models import TaskModel

# Utilisation d'une DB en mémoire pour la rapidité et l'isolation
# StaticPool est CRUCIAL : il maintient la connexion (et donc les données en mémoire) ouverte
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session")
def setup_test_database():
    """Crée les tables une seule fois pour tous les tests."""
    # Crée toutes les tables définies dans les modèles (TaskModel, etc.)
    Base.metadata.create_all(bind=test_engine)
    yield
    # Nettoyage à la fin de la session
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def clear_test_data(setup_test_database):
    """Nettoie les données entre chaque test pour garantir l'isolation."""
    db = TestSessionLocal()
    try:
        db.query(TaskModel).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def client(setup_test_database):
    """Client de test avec base de données isolée."""
    # Surcharge la dépendance get_db pour utiliser notre session de test
    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as c:
        yield c
    
    # Nettoyage de la surcharge après le test
    app.dependency_overrides.clear()