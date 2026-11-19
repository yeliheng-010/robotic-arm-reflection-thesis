"""旧引擎finally会再次render；只观察一次并保留最初退出原因。"""
def once(observe, retain, *, complete):
    terminal = []
    def render(env):
        if terminal:
            raise terminal[0]
        retain(env)
        try:
            observe(env)
        except BaseException as error:
            terminal.append(error)
        else:
            terminal.append(complete())
        raise terminal[0]
    return render
