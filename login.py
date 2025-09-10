from app import app, db, Admin
app.app_context().push()
db.create_all()


if not Admin.query.filter_by(username='admin').first():
    admin_user = Admin(username='admin')
    admin_user.set_password('123')
    db.session.add(admin_user)
    db.session.commit()
    print('Tài khoản admin đã được tạo.')
else:
    print('Tài khoản admin đã tồn tại.')

exit()