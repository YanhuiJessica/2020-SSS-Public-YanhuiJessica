<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Weak Website</title>
</head>
<body>
    <form method="post">
        <input type="text" name="xss">
        <input type="submit" value="提交">
    </form>
    <?php
        if(isset($_POST["xss"]))
        {
            echo $_POST["xss"];
        }
    ?>
</body>
</html>