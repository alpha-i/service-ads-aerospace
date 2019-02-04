from app import services
from app.core.models import User, Company
from app.entities.customer import UserPermissions


def create_admin(email, password):
    alphai_company = services.company.insert(
        Company(name='alphai', domain='alpha-i.co')
    )
    user = User(
        email=email,
        confirmed=True,
        company_id=alphai_company.id,
        password=password,
        permissions=UserPermissions.ADMIN
    )
    user = services.user.insert(user)
    return user
