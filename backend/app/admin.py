"""Admin commands, run from a shell on the server (there is no admin login yet).

python -m app.admin revoke <install_id>
"""

import sys
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.deps import engine
from app.models import Install


def revoke(install_id: uuid.UUID) -> bool:
    with Session(engine) as session:
        install = session.get(Install, install_id)
        if install is None or install.revoked_at is not None:
            return False
        install.revoked_at = func.now()
        session.commit()
        return True


if __name__ == "__main__":
    match sys.argv[1:]:
        case ["revoke", install_id]:
            ok = revoke(uuid.UUID(install_id))
            print("Revoked." if ok else "No active install with that id.")
            sys.exit(0 if ok else 1)
        case _:
            sys.exit(__doc__)
